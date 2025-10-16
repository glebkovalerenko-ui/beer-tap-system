// src-tauri/src/main.rs

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod api_client;

use pcsc::{Context, Scope, ShareMode, Card, Protocols, Error};
use serde::Serialize;
use std::ffi::CString;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{State, Emitter}; 
use tauri_plugin_log::{Target, TargetKind};
use log::{info, error, debug, LevelFilter};

// Структура для хранения общего PC/SC контекста
struct AppState {
    context: Arc<Mutex<Context>>,
}

// Единая структура для ошибок, отправляемых на фронтенд
#[derive(Debug, Serialize, Clone)]
struct AppError {
    message: String,
}
impl From<Error> for AppError { fn from(err: Error) -> Self { AppError { message: err.to_string() } } }
impl From<String> for AppError { fn from(s: String) -> Self { AppError { message: s } } }
impl From<&str> for AppError { fn from(s: &str) -> Self { AppError { message: s.to_string() } } }
impl From<hex::FromHexError> for AppError { fn from(err: hex::FromHexError) -> Self { AppError { message: err.to_string() } } }


// Структура для данных, передаваемых в событии на фронтенд
#[derive(Clone, serde::Serialize)]
struct CardStatusPayload {
    uid: Option<String>,
    error: Option<String>,
}

// Внутренняя функция для получения списка ридеров.
fn list_readers_internal(context_arc: &Arc<Mutex<Context>>) -> Result<Vec<String>, Error> {
    let context = context_arc.lock().unwrap();
    let mut readers_buf = [0; 2048];
    let reader_names = context.list_readers(&mut readers_buf)?;
    Ok(reader_names.map(|name| name.to_string_lossy().into_owned()).collect())
}

// Внутренняя функция для получения UID.
fn get_card_uid_internal(context_arc: &Arc<Mutex<Context>>, reader_name: &str) -> Result<Vec<u8>, Error> {
    let context = context_arc.lock().unwrap();
    let c_reader_name = CString::new(reader_name).unwrap();
    let card = context.connect(&c_reader_name, ShareMode::Shared, Protocols::T0 | Protocols::T1)?;
    const GET_UID_APDU: &[u8] = &[0xFF, 0xCA, 0x00, 0x00, 0x00];
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(GET_UID_APDU, &mut rapdu_buf)?;
    if rapdu.len() < 2 || rapdu[rapdu.len()-2..] != [0x90, 0x00] {
        return Err(Error::Unexpected);
    }
    Ok(rapdu[..rapdu.len()-2].to_vec())
}

// Вспомогательная функция для подключения и аутентификации.
fn connect_and_authenticate(
    context_arc: &Arc<Mutex<Context>>,
    reader_name: &str,
    block_addr: u8,
    key_type: &str,
    key_hex: &str,
) -> Result<Card, AppError> {
    info!("Подключение к '{}' для аутентификации блока {}", reader_name, block_addr);
    let context = context_arc.lock().unwrap();
    let c_reader_name = CString::new(reader_name).map_err(|e| e.to_string())?;
    let card = match context.connect(&c_reader_name, ShareMode::Shared, Protocols::T0 | Protocols::T1) {
        Ok(card) => card,
        Err(err) => {
            error!("Ошибка подключения к карте: {}", err);
            return match err {
                Error::NoSmartcard => Err("Карта не найдена. Поднесите карту к считывателю.".into()),
                _ => Err(format!("Ошибка подключения к карте: {}", err).into()),
            };
        }
    };
    info!("Успешно подключено к карте.");

    let key = hex::decode(key_hex)?;
    if key.len() != 6 { return Err("Ключ должен состоять из 6 байт (12 HEX-символов)".into()); }
    
    let mut load_key_apdu = vec![0xFF, 0x82, 0x00, 0x00, 0x06];
    load_key_apdu.extend_from_slice(&key);
    debug!("> APDU (Load Key): {}", hex::encode(&load_key_apdu));
    
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&load_key_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        error!("< RAPDU (Load Key) Error: {}", hex::encode(rapdu));
        return Err(format!("Ошибка загрузки ключа в ридер: {:?}", hex::encode(rapdu)).into());
    }
    debug!("< RAPDU (Load Key): {}", hex::encode(rapdu));

    let auth_key_type_byte = match key_type { "A" => 0x60, "B" => 0x61, _ => return Err("Неверный тип ключа...".into()) };
    let auth_apdu = &[0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block_addr, auth_key_type_byte, 0x00];
    debug!("> APDU (Authenticate): {}", hex::encode(auth_apdu));

    let rapdu = card.transmit(auth_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        error!("< RAPDU (Authenticate) Error: {}", hex::encode(rapdu));
        return Err("Ошибка аутентификации. Проверьте ключ или номер блока.".into());
    }
    debug!("< RAPDU (Authenticate): {}", hex::encode(rapdu));
    info!("Аутентификация блока {} прошла успешно.", block_addr);

    Ok(card)
}

// --- Команды, вызываемые с фронтенда (NFC) ---

#[tauri::command]
fn list_readers(state: State<AppState>) -> Result<Vec<String>, AppError> {
    info!("[COMMAND] Запрос списка считывателей...");
    let readers_vec = list_readers_internal(&state.context)?;
    info!("[COMMAND] Найдено считывателей: {}", readers_vec.len());
    Ok(readers_vec)
}

#[tauri::command]
fn read_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, state: State<AppState> ) -> Result<String, AppError> {
    info!("[COMMAND] Запрос на чтение блока {}", block_addr);
    let card = connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;

    let read_apdu = &[0xFF, 0xB0, 0x00, block_addr, 0x10];
    debug!("> APDU (Read Block): {}", hex::encode(read_apdu));
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(read_apdu, &mut rapdu_buf)?;
    
    if rapdu.len() < 2 || rapdu[rapdu.len()-2..] != [0x90, 0x00] {
        error!("< RAPDU (Read Block) Error: {}", hex::encode(rapdu));
        return Err(format!("Ошибка чтения блока: {:?}", hex::encode(rapdu)).into());
    }

    let data_hex = hex::encode(&rapdu[..rapdu.len()-2]);
    info!("[COMMAND] Блок {} успешно прочитан. Данные: {}", block_addr, data_hex);
    Ok(data_hex)
}

#[tauri::command]
fn write_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, data_hex: &str, state: State<AppState> ) -> Result<(), AppError> {
    info!("[COMMAND] Запрос на запись в блок {}. Данные: {}", block_addr, data_hex);
    let card = connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;

    let data = hex::decode(data_hex)?;
    if data.len() != 16 { return Err("Данные для записи должны быть 16 байт".into()); }
    
    let mut write_apdu = vec![0xFF, 0xD6, 0x00, block_addr, 0x10];
    write_apdu.extend_from_slice(&data);
    debug!("> APDU (Write Block): {}", hex::encode(&write_apdu));

    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        error!("< RAPDU (Write Block) Error: {}", hex::encode(rapdu));
        return Err(format!("Ошибка записи в блок: {:?}", hex::encode(rapdu)).into());
    }

    info!("[COMMAND] Блок {} успешно записан.", block_addr);
    Ok(())
}

#[tauri::command]
fn change_sector_keys(
    reader_name: &str,
    sector: u8,
    key_type: &str,
    current_key_hex: &str,
    new_key_a: &str,
    new_key_b: &str,
    state: State<AppState>,
) -> Result<(), AppError> {
    info!("[COMMAND] Запрос на смену ключей для сектора {}", sector);
    let trailer_block_addr = (sector * 4) + 3;
    let card = connect_and_authenticate(&state.context, reader_name, trailer_block_addr, key_type, current_key_hex)?;
    let new_key_a_bytes = hex::decode(new_key_a)?;
    let new_key_b_bytes = hex::decode(new_key_b)?;
    if new_key_a_bytes.len() != 6 || new_key_b_bytes.len() != 6 {
        return Err("Новые ключи должны быть длиной 6 байт (12 HEX)".into());
    }
    let access_bits: [u8; 4] = [0xFF, 0x07, 0x80, 0x69]; 
    let mut new_trailer_data: Vec<u8> = Vec::with_capacity(16);
    new_trailer_data.extend_from_slice(&new_key_a_bytes);
    new_trailer_data.extend_from_slice(&access_bits);
    new_trailer_data.extend_from_slice(&new_key_b_bytes);
    let mut write_apdu = vec![0xFF, 0xD6, 0x00, trailer_block_addr, 0x10];
    write_apdu.extend_from_slice(&new_trailer_data);
    debug!("> APDU (Write Trailer): {}", hex::encode(&write_apdu));
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        error!("Ошибка записи в секторный трейлер {}: {}", sector, hex::encode(rapdu));
        return Err("Не удалось записать новый трейлер. Права доступа карты могут не позволять эту операцию с выбранным ключом.".into());
    }
    info!("Секторный трейлер для сектора {} успешно обновлен.", sector);
    Ok(())
}

// --- НОВАЯ КОМАНДА: Получение данных с API ---
#[tauri::command]
async fn get_guests(token: String) -> Result<Vec<api_client::Guest>, AppError> {
    info!("[COMMAND] Запрос списка гостей с API...");
    // Вызываем нашу функцию из api_client и конвертируем ее ошибку (String) в нашу AppError
    api_client::get_guests(&token).await.map_err(AppError::from)
}

// --- НОВАЯ КОМАНДА: Аутентификация пользователя ---
#[tauri::command]
async fn login(username: String, password: String) -> Result<String, AppError> {
    info!("[COMMAND] Попытка входа пользователя: {}", username);

    // Создаем структуру с учетными данными
    let credentials = api_client::LoginCredentials {
        username: &username,
        password: &password,
    };

    // Вызываем нашу новую функцию из api_client и возвращаем результат
    api_client::login(&credentials).await.map_err(AppError::from)
}

// --- НОВАЯ КОМАНДА: Создание гостя ---
#[tauri::command]
async fn create_guest(token: String, guest_data: api_client::GuestPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Запрос на создание нового гостя...");
    api_client::create_guest(&token, &guest_data).await.map_err(AppError::from)
}

fn main() {
    let context = Arc::new(Mutex::new(Context::establish(Scope::User)
        .expect("Не удалось установить PC/SC контекст...")));

    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::new()
            .targets([
                Target::new(TargetKind::Stdout),
                Target::new(TargetKind::Webview),
                Target::new(TargetKind::LogDir { file_name: Some("app".into()) }),
            ])
            .level(LevelFilter::Debug)
            .build())
        .manage(AppState { context: Arc::clone(&context) })
        .invoke_handler(tauri::generate_handler![
            // Существующие команды
            list_readers,
            read_mifare_block,
            write_mifare_block,
            change_sector_keys,
            // <-- Новая команда зарегистрирована здесь
            get_guests,
            login,
            create_guest
        ])
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let context_clone = Arc::clone(&context);
            
            info!("Запуск фонового потока для мониторинга карт...");
            thread::spawn(move || {
                let mut last_uid: Option<Vec<u8>> = None;
                let mut reader_present = false;

                loop {
                    let readers_result = list_readers_internal(&context_clone);
                    let reader_name = match readers_result {
                        Ok(mut names) if !names.is_empty() => {
                            if !reader_present {
                                info!("Считыватель подключен: {}", names[0]);
                                reader_present = true;
                            }
                            names.remove(0)
                        },
                        _ => {
                            if reader_present {
                                info!("Считыватель отключен");
                                reader_present = false;
                                last_uid = None;
                                app_handle.emit("card-status-changed", CardStatusPayload { uid: None, error: Some("Считыватель не найден.".to_string()) }).unwrap();
                            }
                            thread::sleep(Duration::from_secs(2));
                            continue;
                        }
                    };
                    
                    match get_card_uid_internal(&context_clone, &reader_name) {
                        Ok(current_uid_bytes) => {
                            if last_uid.as_deref() != Some(&current_uid_bytes) {
                                info!("Обнаружена новая карта: {}", hex::encode(&current_uid_bytes));
                                last_uid = Some(current_uid_bytes.clone());
                                app_handle.emit("card-status-changed", CardStatusPayload { uid: Some(hex::encode(current_uid_bytes)), error: None }).unwrap();
                            }
                        },
                        Err(_) => {
                            if last_uid.is_some() {
                                info!("Карта убрана");
                                last_uid = None;
                                app_handle.emit("card-status-changed", CardStatusPayload { uid: None, error: None }).unwrap();
                            }
                        }
                    }
                    thread::sleep(Duration::from_millis(500));
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Ошибка при запуске Tauri приложения");
}