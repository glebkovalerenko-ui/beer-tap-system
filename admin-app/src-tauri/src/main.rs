// src-tauri/src/main.rs

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

// --- Модули ---
mod api_client;
mod nfc_handler; 

// --- Зависимости ---
use pcsc::{Context, Scope, Error};
use serde::Serialize;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{State, Emitter}; 
use tauri_plugin_log::{Target, TargetKind};
use log::{info, error, debug};
use serde_json; 
use hex;

// =============================================================================
// СТРУКТУРЫ УРОВНЯ ПРИЛОЖЕНИЯ
// =============================================================================

struct AppState {
    context: Arc<Mutex<Context>>,
}

#[derive(Debug, Serialize, Clone)]
pub struct AppError { 
    message: String,
}
impl From<Error> for AppError { fn from(err: Error) -> Self { AppError { message: err.to_string() } } }
impl From<String> for AppError { fn from(s: String) -> Self { AppError { message: s } } }
impl From<&str> for AppError { fn from(s: &str) -> Self { AppError { message: s.to_string() } } }
impl From<hex::FromHexError> for AppError { fn from(err: hex::FromHexError) -> Self { AppError { message: err.to_string() } } }

#[derive(Clone, serde::Serialize)]
struct CardStatusPayload {
    uid: Option<String>,
    error: Option<String>,
}

// =============================================================================
// TAURI-КОМАНДЫ (мост между Frontend и Rust)
// =============================================================================

// --- Команды для работы с NFC ---
#[tauri::command]
fn list_readers(state: State<AppState>) -> Result<Vec<String>, AppError> {
    // ... (без изменений)
    info!("[COMMAND] Запрос списка считывателей...");
    let readers_vec = nfc_handler::list_readers_internal(&state.context)?;
    info!("[COMMAND] Найдено считывателей: {}", readers_vec.len());
    Ok(readers_vec)
}

#[tauri::command]
fn read_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, state: State<AppState> ) -> Result<String, AppError> {
    // ... (без изменений)
    info!("[COMMAND] Запрос на чтение блока {}", block_addr);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let read_apdu = &[0xFF, 0xB0, 0x00, block_addr, 0x10];
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(read_apdu, &mut rapdu_buf)?;
    if rapdu.len() < 2 || rapdu[rapdu.len()-2..] != [0x90, 0x00] {
        return Err(format!("Ошибка чтения блока: {:?}", hex::encode(rapdu)).into());
    }
    let data_hex = hex::encode(&rapdu[..rapdu.len()-2]);
    info!("[COMMAND] Блок {} успешно прочитан. Данные: {}", block_addr, data_hex);
    Ok(data_hex)
}

#[tauri::command]
fn write_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, data_hex: &str, state: State<AppState> ) -> Result<(), AppError> {
    // ... (без изменений)
    info!("[COMMAND] Запрос на запись в блок {}. Данные: {}", block_addr, data_hex);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let data = hex::decode(data_hex)?;
    if data.len() != 16 { return Err("Данные для записи должны быть 16 байт".into()); }
    let mut write_apdu = vec![0xFF, 0xD6, 0x00, block_addr, 0x10];
    write_apdu.extend_from_slice(&data);
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        return Err(format!("Ошибка записи в блок: {:?}", hex::encode(rapdu)).into());
    }
    info!("[COMMAND] Блок {} успешно записан.", block_addr);
    Ok(())
}

#[tauri::command]
fn change_sector_keys( reader_name: &str, sector: u8, key_type: &str, current_key_hex: &str, new_key_a: &str, new_key_b: &str, state: State<AppState>) -> Result<(), AppError> {
    // ... (без изменений)
    info!("[COMMAND] Запрос на смену ключей для сектора {}", sector);
    let trailer_block_addr = (sector * 4) + 3;
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, trailer_block_addr, key_type, current_key_hex)?;
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
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        return Err("Не удалось записать новый трейлер.".into());
    }
    info!("Секторный трейлер для сектора {} успешно обновлен.", sector);
    Ok(())
}

// --- Команды для работы с API ---
#[tauri::command]
async fn login(username: String, password: String) -> Result<String, AppError> {
    info!("[COMMAND] Попытка входа пользователя: {}", username);
    let credentials = api_client::LoginCredentials { username: &username, password: &password };
    api_client::login(&credentials).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_guests(token: String) -> Result<Vec<api_client::Guest>, AppError> {
    info!("[COMMAND] Запрос списка гостей с API...");
    api_client::get_guests(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_guest(token: String, guest_data: api_client::GuestPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Запрос на создание нового гостя...");
    api_client::create_guest(&token, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_guest(token: String, guest_id: String, guest_data: api_client::GuestUpdatePayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Запрос на обновление гостя ID: {}", guest_id);
    api_client::update_guest(&token, &guest_id, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn bind_card_to_guest(token: String, guest_id: String, card_uid: String) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Запрос на привязку карты UID: {} к гостю ID: {}", card_uid, guest_id);
    api_client::bind_card_to_guest(&token, &guest_id, &card_uid).await.map_err(AppError::from)
}

#[tauri::command]
async fn top_up_balance(token: String, guest_id: String, top_up_data: api_client::TopUpPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Запрос на пополнение баланса для гостя ID: {}", guest_id);
    api_client::top_up_balance(&token, &guest_id, &top_up_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_kegs(token: String) -> Result<Vec<api_client::Keg>, AppError> {
    info!("[COMMAND] Запрос списка кег с API...");
    api_client::get_kegs(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_keg(token: String, keg_data: api_client::KegPayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND] Запрос на создание новой кеги...");
    api_client::create_keg(&token, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_keg(token: String, keg_id: String, keg_data: api_client::KegUpdatePayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND] Запрос на обновление кеги ID: {}", keg_id);
    api_client::update_keg(&token, &keg_id, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn delete_keg(token: String, keg_id: String) -> Result<(), AppError> {
    info!("[COMMAND] Запрос на удаление кеги ID: {}", keg_id);
    api_client::delete_keg(&token, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_taps(token: String) -> Result<Vec<api_client::Tap>, AppError> {
    info!("[COMMAND] Запрос списка кранов с API...");
    api_client::get_taps(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_pours(token: String, limit: u32) -> Result<Vec<api_client::PourResponse>, AppError> {
    info!("[COMMAND] Запрос списка наливов с API...");
    api_client::get_pours(&token, limit).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_beverages(token: String) -> Result<Vec<api_client::Beverage>, AppError> {
    info!("[COMMAND] Запрос списка напитков с API...");
    api_client::get_beverages(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_beverage(token: String, beverage_data: api_client::BeveragePayload) -> Result<api_client::Beverage, AppError> {
    info!("[COMMAND] Запрос на создание нового напитка...");
    api_client::create_beverage(&token, &beverage_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn assign_keg_to_tap(token: String, tap_id: i32, keg_id: String) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Запрос на назначение кеги ID: {} на кран ID: {}", keg_id, tap_id);
    api_client::assign_keg_to_tap(&token, tap_id, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn unassign_keg_from_tap(token: String, tap_id: i32) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Запрос на снятие кеги с крана ID: {}", tap_id);
    api_client::unassign_keg_from_tap(&token, tap_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_tap(token: String, tap_id: i32, payload: api_client::TapUpdatePayload) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Запрос на обновление крана ID: {}", tap_id);
    api_client::update_tap(&token, tap_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_system_status(token: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND] Запрос статуса системы...");
    api_client::get_system_status(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn set_emergency_stop(token: String, value: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND] Запрос на изменение статуса Emergency Stop на '{}'", value);
    let payload = api_client::SystemStateUpdatePayload { value };
    api_client::set_emergency_stop(&token, &payload).await.map_err(AppError::from)
}


#[tauri::command]
async fn search_active_visit(token: String, query: String) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Поиск активного визита по строке запроса...");
    api_client::search_active_visit(&token, &query).await.map_err(AppError::from)
}

#[tauri::command]
async fn open_visit(token: String, guest_id: String, card_uid: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Открытие визита для гостя ID: {}", guest_id);
    let payload = api_client::VisitOpenPayload { guest_id, card_uid };
    api_client::open_visit(&token, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn force_unlock_visit(token: String, visit_id: String, reason: String, comment: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Force unlock для визита ID: {}", visit_id);
    let payload = api_client::VisitForceUnlockPayload { reason, comment };
    api_client::force_unlock_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn close_visit(token: String, visit_id: String, closed_reason: String, card_returned: bool) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Закрытие визита ID: {}", visit_id);
    let payload = api_client::VisitClosePayload { closed_reason, card_returned };
    api_client::close_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

// =============================================================================
// ТОЧКА ВХОДА ПРИЛОЖЕНИЯ
// =============================================================================

fn main() {
    // ... (panic_hook и PC/SC context без изменений)
    let default_panic_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        error!("!!! THREAD PANICKED !!!: {}", panic_info);
        default_panic_hook(panic_info);
    }));

    let context = Arc::new(Mutex::new(Context::establish(Scope::User)
        .expect("Не удалось установить PC/SC контекст...")));

    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::new()
            .targets([
                Target::new(TargetKind::Stdout),
                Target::new(TargetKind::Webview),
                Target::new(TargetKind::LogDir { file_name: Some("app".into()) }),
            ])
            .level(log::LevelFilter::Debug)
            .build())
        .manage(AppState { context: Arc::clone(&context) })
        // --- ИЗМЕНЕНИЕ: Добавлены новые команды в обработчик ---
        .invoke_handler(tauri::generate_handler![
            // NFC
            list_readers,
            read_mifare_block,
            write_mifare_block,
            change_sector_keys,
            // API - Guests
            login,
            get_guests,
            create_guest,
            update_guest,
            bind_card_to_guest,
            top_up_balance,
            // API - Kegs & Taps
            get_kegs,
            create_keg,
            update_keg,
            delete_keg,
            get_taps,
            get_pours,
            // API - Beverages
            get_beverages,
            create_beverage,
            assign_keg_to_tap,
            unassign_keg_from_tap,
            update_tap,
            // API - System
            get_system_status,
            set_emergency_stop,
            // API - Visits
            search_active_visit,
            open_visit,
            force_unlock_visit,
            close_visit
        ])
        .setup(move |app| {
            // ... (фоновый поток NFC без изменений)
            let app_handle = app.handle().clone();
            let context_clone = Arc::clone(&context);
            
            info!("Запуск фонового потока для мониторинга карт...");
            // Вставь этот код вместо старого thread::spawn
            thread::spawn(move || {
                let mut last_payload_json = String::new(); // Идемпотентность события на фронтенде

                loop {
                    let payload = match nfc_handler::list_readers_internal(&context_clone) {
                        // ШАБЛОН: Ридеры найдены и список НЕ пуст
                        Ok(mut names) if !names.is_empty() => {
                            let reader_name = names.remove(0);
                            // Ридер найден. Пытаемся прочитать карту.
                            match nfc_handler::get_card_uid_internal(&context_clone, &reader_name) {
                                Ok(uid_bytes) => {
                                    // Карта найдена.
                                    CardStatusPayload { uid: Some(hex::encode(uid_bytes)), error: None }
                                },
                                Err(pcsc::Error::NoSmartcard) | Err(pcsc::Error::RemovedCard) => {
                                    // Ридер есть, но карты нет (или убрали). Это штатный, "рабочий" статус.
                                    CardStatusPayload { uid: None, error: None }
                                },
                                Err(e) => {
                                    // Другая ошибка PC/SC, но ридер виден.
                                    error!("Ошибка чтения карты (ридер доступен): {}", e);
                                    CardStatusPayload { uid: None, error: Some(e.to_string()) }
                                }
                            }
                        },
                        // +++ НОВЫЙ ШАБЛОН: Ридеры найдены, но список ПУСТ (логически невозможно, но Rust требует)
                        Ok(_) => {
                            error!("Ошибка: список ридеров пуст, хотя контекст ОК.");
                            CardStatusPayload { uid: None, error: Some("Считыватель не найден.".to_string()) }
                        }
                        // ШАБЛОН: Ридер не найден из-за ошибки PC/SC
                        Err(e) => {
                            // Ридер не найден или глобальная ошибка контекста.
                            error!("Глобальная ошибка PC/SC: {}", e);
                            CardStatusPayload { uid: None, error: Some("Считыватель не найден.".to_string()) }
                        }
                    };
                    
                    // Отправляем событие, только если текущий payload отличается от предыдущего.
                    match serde_json::to_string(&payload) {
                        Ok(current_payload_json) => {
                            if current_payload_json != last_payload_json {
                                info!("Статус NFC изменился, отправка события: {}", current_payload_json);
                                if let Err(e) = app_handle.emit("card-status-changed", payload.clone()) { // Добавил .clone()
                                    error!("Не удалось отправить событие card-status-changed: {}", e);
                                }
                                last_payload_json = current_payload_json;
                            }
                        },
                        Err(e) => {
                            error!("Не удалось сериализовать payload: {}", e);
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