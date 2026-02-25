// src-tauri/src/main.rs

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

// --- РњРѕРґСѓР»Рё ---
mod api_client;
mod nfc_handler; 

// --- Р—Р°РІРёСЃРёРјРѕСЃС‚Рё ---
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
// РЎРўР РЈРљРўРЈР Р« РЈР РћР’РќРЇ РџР РР›РћР–Р•РќРРЇ
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
// TAURI-РљРћРњРђРќР”Р« (РјРѕСЃС‚ РјРµР¶РґСѓ Frontend Рё Rust)
// =============================================================================

// --- РљРѕРјР°РЅРґС‹ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ NFC ---
#[tauri::command]
fn list_readers(state: State<AppState>) -> Result<Vec<String>, AppError> {
    // ... (Р±РµР· РёР·РјРµРЅРµРЅРёР№)
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° СЃС‡РёС‚С‹РІР°С‚РµР»РµР№...");
    let readers_vec = nfc_handler::list_readers_internal(&state.context)?;
    info!("[COMMAND] РќР°Р№РґРµРЅРѕ СЃС‡РёС‚С‹РІР°С‚РµР»РµР№: {}", readers_vec.len());
    Ok(readers_vec)
}

#[tauri::command]
fn read_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, state: State<AppState> ) -> Result<String, AppError> {
    // ... (Р±РµР· РёР·РјРµРЅРµРЅРёР№)
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° С‡С‚РµРЅРёРµ Р±Р»РѕРєР° {}", block_addr);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let read_apdu = &[0xFF, 0xB0, 0x00, block_addr, 0x10];
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(read_apdu, &mut rapdu_buf)?;
    if rapdu.len() < 2 || rapdu[rapdu.len()-2..] != [0x90, 0x00] {
        return Err(format!("РћС€РёР±РєР° С‡С‚РµРЅРёСЏ Р±Р»РѕРєР°: {:?}", hex::encode(rapdu)).into());
    }
    let data_hex = hex::encode(&rapdu[..rapdu.len()-2]);
    info!("[COMMAND] Р‘Р»РѕРє {} СѓСЃРїРµС€РЅРѕ РїСЂРѕС‡РёС‚Р°РЅ. Р”Р°РЅРЅС‹Рµ: {}", block_addr, data_hex);
    Ok(data_hex)
}

#[tauri::command]
fn write_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, data_hex: &str, state: State<AppState> ) -> Result<(), AppError> {
    // ... (Р±РµР· РёР·РјРµРЅРµРЅРёР№)
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° Р·Р°РїРёСЃСЊ РІ Р±Р»РѕРє {}. Р”Р°РЅРЅС‹Рµ: {}", block_addr, data_hex);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let data = hex::decode(data_hex)?;
    if data.len() != 16 { return Err("Р”Р°РЅРЅС‹Рµ РґР»СЏ Р·Р°РїРёСЃРё РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ 16 Р±Р°Р№С‚".into()); }
    let mut write_apdu = vec![0xFF, 0xD6, 0x00, block_addr, 0x10];
    write_apdu.extend_from_slice(&data);
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        return Err(format!("РћС€РёР±РєР° Р·Р°РїРёСЃРё РІ Р±Р»РѕРє: {:?}", hex::encode(rapdu)).into());
    }
    info!("[COMMAND] Р‘Р»РѕРє {} СѓСЃРїРµС€РЅРѕ Р·Р°РїРёСЃР°РЅ.", block_addr);
    Ok(())
}

#[tauri::command]
fn change_sector_keys( reader_name: &str, sector: u8, key_type: &str, current_key_hex: &str, new_key_a: &str, new_key_b: &str, state: State<AppState>) -> Result<(), AppError> {
    // ... (Р±РµР· РёР·РјРµРЅРµРЅРёР№)
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СЃРјРµРЅСѓ РєР»СЋС‡РµР№ РґР»СЏ СЃРµРєС‚РѕСЂР° {}", sector);
    let trailer_block_addr = (sector * 4) + 3;
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, trailer_block_addr, key_type, current_key_hex)?;
    let new_key_a_bytes = hex::decode(new_key_a)?;
    let new_key_b_bytes = hex::decode(new_key_b)?;
    if new_key_a_bytes.len() != 6 || new_key_b_bytes.len() != 6 {
        return Err("РќРѕРІС‹Рµ РєР»СЋС‡Рё РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ РґР»РёРЅРѕР№ 6 Р±Р°Р№С‚ (12 HEX)".into());
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
        return Err("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РїРёСЃР°С‚СЊ РЅРѕРІС‹Р№ С‚СЂРµР№Р»РµСЂ.".into());
    }
    info!("РЎРµРєС‚РѕСЂРЅС‹Р№ С‚СЂРµР№Р»РµСЂ РґР»СЏ СЃРµРєС‚РѕСЂР° {} СѓСЃРїРµС€РЅРѕ РѕР±РЅРѕРІР»РµРЅ.", sector);
    Ok(())
}

// --- РљРѕРјР°РЅРґС‹ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ API ---
#[tauri::command]
async fn login(username: String, password: String) -> Result<String, AppError> {
    info!("[COMMAND] РџРѕРїС‹С‚РєР° РІС…РѕРґР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ: {}", username);
    let credentials = api_client::LoginCredentials { username: &username, password: &password };
    api_client::login(&credentials).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_guests(token: String) -> Result<Vec<api_client::Guest>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° РіРѕСЃС‚РµР№ СЃ API...");
    api_client::get_guests(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_guest(token: String, guest_data: api_client::GuestPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СЃРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ РіРѕСЃС‚СЏ...");
    api_client::create_guest(&token, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_guest(token: String, guest_id: String, guest_data: api_client::GuestUpdatePayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РѕР±РЅРѕРІР»РµРЅРёРµ РіРѕСЃС‚СЏ ID: {}", guest_id);
    api_client::update_guest(&token, &guest_id, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn bind_card_to_guest(token: String, guest_id: String, card_uid: String) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РїСЂРёРІСЏР·РєСѓ РєР°СЂС‚С‹ UID: {} Рє РіРѕСЃС‚СЋ ID: {}", card_uid, guest_id);
    api_client::bind_card_to_guest(&token, &guest_id, &card_uid).await.map_err(AppError::from)
}

#[tauri::command]
async fn top_up_balance(token: String, guest_id: String, top_up_data: api_client::TopUpPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РїРѕРїРѕР»РЅРµРЅРёРµ Р±Р°Р»Р°РЅСЃР° РґР»СЏ РіРѕСЃС‚СЏ ID: {}", guest_id);
    api_client::top_up_balance(&token, &guest_id, &top_up_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_kegs(token: String) -> Result<Vec<api_client::Keg>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° РєРµРі СЃ API...");
    api_client::get_kegs(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_keg(token: String, keg_data: api_client::KegPayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СЃРѕР·РґР°РЅРёРµ РЅРѕРІРѕР№ РєРµРіРё...");
    api_client::create_keg(&token, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_keg(token: String, keg_id: String, keg_data: api_client::KegUpdatePayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РѕР±РЅРѕРІР»РµРЅРёРµ РєРµРіРё ID: {}", keg_id);
    api_client::update_keg(&token, &keg_id, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn delete_keg(token: String, keg_id: String) -> Result<(), AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СѓРґР°Р»РµРЅРёРµ РєРµРіРё ID: {}", keg_id);
    api_client::delete_keg(&token, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_taps(token: String) -> Result<Vec<api_client::Tap>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° РєСЂР°РЅРѕРІ СЃ API...");
    api_client::get_taps(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_pours(token: String, limit: u32) -> Result<Vec<api_client::PourResponse>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° РЅР°Р»РёРІРѕРІ СЃ API...");
    api_client::get_pours(&token, limit).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_beverages(token: String) -> Result<Vec<api_client::Beverage>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° РЅР°РїРёС‚РєРѕРІ СЃ API...");
    api_client::get_beverages(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_beverage(token: String, beverage_data: api_client::BeveragePayload) -> Result<api_client::Beverage, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СЃРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ РЅР°РїРёС‚РєР°...");
    api_client::create_beverage(&token, &beverage_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn assign_keg_to_tap(token: String, tap_id: i32, keg_id: String) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РЅР°Р·РЅР°С‡РµРЅРёРµ РєРµРіРё ID: {} РЅР° РєСЂР°РЅ ID: {}", keg_id, tap_id);
    api_client::assign_keg_to_tap(&token, tap_id, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn unassign_keg_from_tap(token: String, tap_id: i32) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° СЃРЅСЏС‚РёРµ РєРµРіРё СЃ РєСЂР°РЅР° ID: {}", tap_id);
    api_client::unassign_keg_from_tap(&token, tap_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_tap(token: String, tap_id: i32, payload: api_client::TapUpdatePayload) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РѕР±РЅРѕРІР»РµРЅРёРµ РєСЂР°РЅР° ID: {}", tap_id);
    api_client::update_tap(&token, tap_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_system_status(token: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃС‚Р°С‚СѓСЃР° СЃРёСЃС‚РµРјС‹...");
    api_client::get_system_status(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn set_emergency_stop(token: String, value: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ РЅР° РёР·РјРµРЅРµРЅРёРµ СЃС‚Р°С‚СѓСЃР° Emergency Stop РЅР° '{}'", value);
    let payload = api_client::SystemStateUpdatePayload { value };
    api_client::set_emergency_stop(&token, &payload).await.map_err(AppError::from)
}


#[tauri::command]
async fn get_active_visits(token: String) -> Result<Vec<api_client::VisitActiveListItem>, AppError> {
    info!("[COMMAND] Р—Р°РїСЂРѕСЃ СЃРїРёСЃРєР° Р°РєС‚РёРІРЅС‹С… РІРёР·РёС‚РѕРІ...");
    api_client::get_active_visits(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn search_active_visit(token: String, query: String) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] РџРѕРёСЃРє Р°РєС‚РёРІРЅРѕРіРѕ РІРёР·РёС‚Р° РїРѕ СЃС‚СЂРѕРєРµ Р·Р°РїСЂРѕСЃР°...");
    api_client::search_active_visit(&token, &query).await.map_err(AppError::from)
}

#[tauri::command]
async fn open_visit(token: String, guest_id: String, card_uid: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] РћС‚РєСЂС‹С‚РёРµ РІРёР·РёС‚Р° РґР»СЏ РіРѕСЃС‚СЏ ID: {}", guest_id);
    let payload = api_client::VisitOpenPayload { guest_id, card_uid };
    api_client::open_visit(&token, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn assign_card_to_visit(token: String, visit_id: String, card_uid: String) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] РџСЂРёРІСЏР·РєР° РєР°СЂС‚С‹ Рє РІРёР·РёС‚Сѓ ID: {}", visit_id);
    let payload = api_client::VisitAssignCardPayload { card_uid };
    api_client::assign_card_to_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn force_unlock_visit(token: String, visit_id: String, reason: String, comment: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Force unlock РґР»СЏ РІРёР·РёС‚Р° ID: {}", visit_id);
    let payload = api_client::VisitForceUnlockPayload { reason, comment };
    api_client::force_unlock_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn close_visit(token: String, visit_id: String, closed_reason: String, card_returned: bool) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Р—Р°РєСЂС‹С‚РёРµ РІРёР·РёС‚Р° ID: {}", visit_id);
    let payload = api_client::VisitClosePayload { closed_reason, card_returned };
    api_client::close_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn reconcile_pour(
    token: String,
    visit_id: String,
    tap_id: i32,
    short_id: String,
    volume_ml: i32,
    amount: String,
    reason: String,
    comment: Option<String>,
) -> Result<api_client::Visit, AppError> {
    let payload = api_client::VisitReconcilePourPayload {
        tap_id,
        short_id,
        volume_ml,
        amount,
        reason,
        comment,
    };
    api_client::reconcile_pour(&token, &visit_id, &payload).await.map_err(AppError::from)
}

// =============================================================================
// РўРћР§РљРђ Р’РҐРћР”Рђ РџР РР›РћР–Р•РќРРЇ
// =============================================================================

fn main() {
    // ... (panic_hook Рё PC/SC context Р±РµР· РёР·РјРµРЅРµРЅРёР№)
    let default_panic_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        error!("!!! THREAD PANICKED !!!: {}", panic_info);
        default_panic_hook(panic_info);
    }));

    let context = Arc::new(Mutex::new(Context::establish(Scope::User)
        .expect("РќРµ СѓРґР°Р»РѕСЃСЊ СѓСЃС‚Р°РЅРѕРІРёС‚СЊ PC/SC РєРѕРЅС‚РµРєСЃС‚...")));

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
        // --- РР—РњР•РќР•РќРР•: Р”РѕР±Р°РІР»РµРЅС‹ РЅРѕРІС‹Рµ РєРѕРјР°РЅРґС‹ РІ РѕР±СЂР°Р±РѕС‚С‡РёРє ---
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
            get_active_visits,
            search_active_visit,
            open_visit,
            assign_card_to_visit,
            force_unlock_visit,
            close_visit,
            reconcile_pour
        ])
        .setup(move |app| {
            // ... (С„РѕРЅРѕРІС‹Р№ РїРѕС‚РѕРє NFC Р±РµР· РёР·РјРµРЅРµРЅРёР№)
            let app_handle = app.handle().clone();
            let context_clone = Arc::clone(&context);
            
            info!("Р—Р°РїСѓСЃРє С„РѕРЅРѕРІРѕРіРѕ РїРѕС‚РѕРєР° РґР»СЏ РјРѕРЅРёС‚РѕСЂРёРЅРіР° РєР°СЂС‚...");
            // Р’СЃС‚Р°РІСЊ СЌС‚РѕС‚ РєРѕРґ РІРјРµСЃС‚Рѕ СЃС‚Р°СЂРѕРіРѕ thread::spawn
            thread::spawn(move || {
                let mut last_payload_json = String::new(); // РРґРµРјРїРѕС‚РµРЅС‚РЅРѕСЃС‚СЊ СЃРѕР±С‹С‚РёСЏ РЅР° С„СЂРѕРЅС‚РµРЅРґРµ

                loop {
                    let payload = match nfc_handler::list_readers_internal(&context_clone) {
                        // РЁРђР‘Р›РћРќ: Р РёРґРµСЂС‹ РЅР°Р№РґРµРЅС‹ Рё СЃРїРёСЃРѕРє РќР• РїСѓСЃС‚
                        Ok(mut names) if !names.is_empty() => {
                            let reader_name = names.remove(0);
                            // Р РёРґРµСЂ РЅР°Р№РґРµРЅ. РџС‹С‚Р°РµРјСЃСЏ РїСЂРѕС‡РёС‚Р°С‚СЊ РєР°СЂС‚Сѓ.
                            match nfc_handler::get_card_uid_internal(&context_clone, &reader_name) {
                                Ok(uid_bytes) => {
                                    // РљР°СЂС‚Р° РЅР°Р№РґРµРЅР°.
                                    CardStatusPayload { uid: Some(hex::encode(uid_bytes)), error: None }
                                },
                                Err(pcsc::Error::NoSmartcard) | Err(pcsc::Error::RemovedCard) => {
                                    // Р РёРґРµСЂ РµСЃС‚СЊ, РЅРѕ РєР°СЂС‚С‹ РЅРµС‚ (РёР»Рё СѓР±СЂР°Р»Рё). Р­С‚Рѕ С€С‚Р°С‚РЅС‹Р№, "СЂР°Р±РѕС‡РёР№" СЃС‚Р°С‚СѓСЃ.
                                    CardStatusPayload { uid: None, error: None }
                                },
                                Err(e) => {
                                    // Р”СЂСѓРіР°СЏ РѕС€РёР±РєР° PC/SC, РЅРѕ СЂРёРґРµСЂ РІРёРґРµРЅ.
                                    error!("РћС€РёР±РєР° С‡С‚РµРЅРёСЏ РєР°СЂС‚С‹ (СЂРёРґРµСЂ РґРѕСЃС‚СѓРїРµРЅ): {}", e);
                                    CardStatusPayload { uid: None, error: Some(e.to_string()) }
                                }
                            }
                        },
                        // +++ РќРћР’Р«Р™ РЁРђР‘Р›РћРќ: Р РёРґРµСЂС‹ РЅР°Р№РґРµРЅС‹, РЅРѕ СЃРїРёСЃРѕРє РџРЈРЎРў (Р»РѕРіРёС‡РµСЃРєРё РЅРµРІРѕР·РјРѕР¶РЅРѕ, РЅРѕ Rust С‚СЂРµР±СѓРµС‚)
                        Ok(_) => {
                            error!("РћС€РёР±РєР°: СЃРїРёСЃРѕРє СЂРёРґРµСЂРѕРІ РїСѓСЃС‚, С…РѕС‚СЏ РєРѕРЅС‚РµРєСЃС‚ РћРљ.");
                            CardStatusPayload { uid: None, error: Some("РЎС‡РёС‚С‹РІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ.".to_string()) }
                        }
                        // РЁРђР‘Р›РћРќ: Р РёРґРµСЂ РЅРµ РЅР°Р№РґРµРЅ РёР·-Р·Р° РѕС€РёР±РєРё PC/SC
                        Err(e) => {
                            // Р РёРґРµСЂ РЅРµ РЅР°Р№РґРµРЅ РёР»Рё РіР»РѕР±Р°Р»СЊРЅР°СЏ РѕС€РёР±РєР° РєРѕРЅС‚РµРєСЃС‚Р°.
                            error!("Р“Р»РѕР±Р°Р»СЊРЅР°СЏ РѕС€РёР±РєР° PC/SC: {}", e);
                            CardStatusPayload { uid: None, error: Some("РЎС‡РёС‚С‹РІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ.".to_string()) }
                        }
                    };
                    
                    // РћС‚РїСЂР°РІР»СЏРµРј СЃРѕР±С‹С‚РёРµ, С‚РѕР»СЊРєРѕ РµСЃР»Рё С‚РµРєСѓС‰РёР№ payload РѕС‚Р»РёС‡Р°РµС‚СЃСЏ РѕС‚ РїСЂРµРґС‹РґСѓС‰РµРіРѕ.
                    match serde_json::to_string(&payload) {
                        Ok(current_payload_json) => {
                            if current_payload_json != last_payload_json {
                                info!("РЎС‚Р°С‚СѓСЃ NFC РёР·РјРµРЅРёР»СЃСЏ, РѕС‚РїСЂР°РІРєР° СЃРѕР±С‹С‚РёСЏ: {}", current_payload_json);
                                if let Err(e) = app_handle.emit("card-status-changed", payload.clone()) { // Р”РѕР±Р°РІРёР» .clone()
                                    error!("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ СЃРѕР±С‹С‚РёРµ card-status-changed: {}", e);
                                }
                                last_payload_json = current_payload_json;
                            }
                        },
                        Err(e) => {
                            error!("РќРµ СѓРґР°Р»РѕСЃСЊ СЃРµСЂРёР°Р»РёР·РѕРІР°С‚СЊ payload: {}", e);
                        }
                    }

                    thread::sleep(Duration::from_millis(500));
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("РћС€РёР±РєР° РїСЂРё Р·Р°РїСѓСЃРєРµ Tauri РїСЂРёР»РѕР¶РµРЅРёСЏ");
}

