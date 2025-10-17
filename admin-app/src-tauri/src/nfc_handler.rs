// src-tauri/src/nfc_handler.rs

//! Модуль для инкапсуляции всей низкоуровневой логики работы с NFC-считывателем через PC/SC.
//! This module encapsulates all low-level logic for interacting with the NFC reader via PC/SC.

// +++ НАЧАЛО ИЗМЕНЕНИЙ: Убираем неиспользуемый 'Scope' для устранения предупреждения компилятора. +++
use pcsc::{Context, Card, Error, Protocols, ShareMode};
// +++ КОНЕЦ ИЗМЕНЕНИЙ +++
use log::{debug, error, info};
use std::ffi::CString;
use std::sync::{Arc, Mutex};
use super::AppError; // Используем общую структуру ошибок из main.rs

// --- Публичные функции, которые будут использоваться в main.rs ---
// КОММЕНТАРИЙ: Содержимое этих функций не изменилось.

/// Внутренняя функция для получения списка ридеров.
/// Internal function to get the list of readers.
pub fn list_readers_internal(context_arc: &Arc<Mutex<Context>>) -> Result<Vec<String>, Error> {
    let context = context_arc.lock().unwrap();
    let mut readers_buf = [0; 2048];
    let reader_names = context.list_readers(&mut readers_buf)?;
    Ok(reader_names
        .map(|name| name.to_string_lossy().into_owned())
        .collect())
}

/// Внутренняя функция для получения UID карты.
/// Internal function to get the card's UID.
pub fn get_card_uid_internal(
    context_arc: &Arc<Mutex<Context>>,
    reader_name: &str,
) -> Result<Vec<u8>, Error> {
    let context = context_arc.lock().unwrap();
    let c_reader_name = CString::new(reader_name).unwrap();
    let card = context.connect(&c_reader_name, ShareMode::Shared, Protocols::T0 | Protocols::T1)?;
    const GET_UID_APDU: &[u8] = &[0xFF, 0xCA, 0x00, 0x00, 0x00];
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(GET_UID_APDU, &mut rapdu_buf)?;
    if rapdu.len() < 2 || rapdu[rapdu.len() - 2..] != [0x90, 0x00] {
        return Err(Error::Unexpected);
    }
    Ok(rapdu[..rapdu.len() - 2].to_vec())
}

/// Вспомогательная функция для подключения и аутентификации.
/// Helper function to connect and authenticate.
pub fn connect_and_authenticate(
    context_arc: &Arc<Mutex<Context>>,
    reader_name: &str,
    block_addr: u8,
    key_type: &str,
    key_hex: &str,
) -> Result<Card, AppError> {
    info!(
        "Подключение к '{}' для аутентификации блока {}",
        reader_name, block_addr
    );
    let context = context_arc.lock().unwrap();
    let c_reader_name = CString::new(reader_name).map_err(|e| e.to_string())?;
    let card = match context.connect(&c_reader_name, ShareMode::Shared, Protocols::T0 | Protocols::T1)
    {
        Ok(card) => card,
        Err(err) => {
            error!("Ошибка подключения к карте: {}", err);
            return match err {
                Error::NoSmartcard => {
                    Err("Карта не найдена. Поднесите карту к считывателю.".into())
                }
                _ => Err(format!("Ошибка подключения к карте: {}", err).into()),
            };
        }
    };
    info!("Успешно подключено к карте.");

    let key = hex::decode(key_hex)?;
    if key.len() != 6 {
        return Err("Ключ должен состоять из 6 байт (12 HEX-символов)".into());
    }

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

    let auth_key_type_byte = match key_type {
        "A" => 0x60,
        "B" => 0x61,
        _ => return Err("Неверный тип ключа...".into()),
    };
    let auth_apdu = &[
        0xFF,
        0x86,
        0x00,
        0x00,
        0x05,
        0x01,
        0x00,
        block_addr,
        auth_key_type_byte,
        0x00,
    ];
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