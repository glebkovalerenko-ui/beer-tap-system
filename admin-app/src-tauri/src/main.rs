// src-tauri/src/main.rs

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

// ---  ---
mod api_client;
mod nfc_handler; 

// ---  ---
use pcsc::{Context, Scope, Error};
use serde::Serialize;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{State, Emitter}; 
use tauri_plugin_log::{Target, TargetKind};
use log::{info, error};
use serde_json; 
use hex;

// =============================================================================
//   
// =============================================================================

struct AppState {
    context: Arc<Mutex<Context>>,
}

#[derive(Debug, Serialize, Clone)]
pub struct AppError { 
    message: String,
}
fn ensure_error_message(message: String) -> String {
    let trimmed = message.trim();
    if trimmed.is_empty() {
        "Unknown error".to_string()
    } else {
        trimmed.to_string()
    }
}
impl From<Error> for AppError { fn from(err: Error) -> Self { AppError { message: ensure_error_message(err.to_string()) } } }
impl From<String> for AppError { fn from(s: String) -> Self { AppError { message: ensure_error_message(s) } } }
impl From<&str> for AppError { fn from(s: &str) -> Self { AppError { message: ensure_error_message(s.to_string()) } } }
impl From<hex::FromHexError> for AppError { fn from(err: hex::FromHexError) -> Self { AppError { message: ensure_error_message(err.to_string()) } } }

#[derive(Clone, serde::Serialize)]
struct CardStatusPayload {
    uid: Option<String>,
    error: Option<String>,
}

// =============================================================================
// TAURI- (  Frontend  Rust)
// =============================================================================

// ---     NFC ---
#[tauri::command]
fn list_readers(state: State<AppState>) -> Result<Vec<String>, AppError> {
    // ... ( )
    info!("[COMMAND]   ...");
    let readers_vec = nfc_handler::list_readers_internal(&state.context)?;
    info!("[COMMAND]  : {}", readers_vec.len());
    Ok(readers_vec)
}

#[tauri::command]
fn read_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, state: State<AppState> ) -> Result<String, AppError> {
    // ... ( )
    info!("[COMMAND]     {}", block_addr);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let read_apdu = &[0xFF, 0xB0, 0x00, block_addr, 0x10];
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(read_apdu, &mut rapdu_buf)?;
    if rapdu.len() < 2 || rapdu[rapdu.len()-2..] != [0x90, 0x00] {
        return Err(format!("  : {:?}", hex::encode(rapdu)).into());
    }
    let data_hex = hex::encode(&rapdu[..rapdu.len()-2]);
    info!("[COMMAND]  {}  . : {}", block_addr, data_hex);
    Ok(data_hex)
}

#[tauri::command]
fn write_mifare_block( reader_name: &str, block_addr: u8, key_type: &str, key_hex: &str, data_hex: &str, state: State<AppState> ) -> Result<(), AppError> {
    // ... ( )
    info!("[COMMAND]      {}. : {}", block_addr, data_hex);
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, block_addr, key_type, key_hex)?;
    let data = hex::decode(data_hex)?;
    if data.len() != 16 { return Err("     16 ".into()); }
    let mut write_apdu = vec![0xFF, 0xD6, 0x00, block_addr, 0x10];
    write_apdu.extend_from_slice(&data);
    let mut rapdu_buf = [0; 256];
    let rapdu = card.transmit(&write_apdu, &mut rapdu_buf)?;
    if rapdu != [0x90, 0x00] {
        return Err(format!("   : {:?}", hex::encode(rapdu)).into());
    }
    info!("[COMMAND]  {}  .", block_addr);
    Ok(())
}

#[tauri::command]
fn change_sector_keys( reader_name: &str, sector: u8, key_type: &str, current_key_hex: &str, new_key_a: &str, new_key_b: &str, state: State<AppState>) -> Result<(), AppError> {
    // ... ( )
    info!("[COMMAND]       {}", sector);
    let trailer_block_addr = (sector * 4) + 3;
    let card = nfc_handler::connect_and_authenticate(&state.context, reader_name, trailer_block_addr, key_type, current_key_hex)?;
    let new_key_a_bytes = hex::decode(new_key_a)?;
    let new_key_b_bytes = hex::decode(new_key_b)?;
    if new_key_a_bytes.len() != 6 || new_key_b_bytes.len() != 6 {
        return Err("     6  (12 HEX)".into());
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
        return Err("    .".into());
    }
    info!("    {}  .", sector);
    Ok(())
}

// ---     API ---
#[tauri::command]
async fn login(username: String, password: String) -> Result<String, AppError> {
    info!("[COMMAND]   : {}", username);
    let credentials = api_client::LoginCredentials { username: &username, password: &password };
    api_client::login(&credentials).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_guests(token: String) -> Result<Vec<api_client::Guest>, AppError> {
    info!("[COMMAND]     API...");
    api_client::get_guests(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_guest(token: String, guest_data: api_client::GuestPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND]     ...");
    api_client::create_guest(&token, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_guest(token: String, guest_id: String, guest_data: api_client::GuestUpdatePayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND]     ID: {}", guest_id);
    api_client::update_guest(&token, &guest_id, &guest_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn bind_card_to_guest(token: String, guest_id: String, card_uid: String) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND]     UID: {}   ID: {}", card_uid, guest_id);
    api_client::bind_card_to_guest(&token, &guest_id, &card_uid).await.map_err(AppError::from)
}

#[tauri::command]
async fn top_up_balance(token: String, guest_id: String, top_up_data: api_client::TopUpPayload) -> Result<api_client::Guest, AppError> {
    info!("[COMMAND]       ID: {}", guest_id);
    api_client::top_up_balance(&token, &guest_id, &top_up_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_kegs(token: String) -> Result<Vec<api_client::Keg>, AppError> {
    info!("[COMMAND]     API...");
    api_client::get_kegs(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_keg(token: String, keg_data: api_client::KegPayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND]     ...");
    api_client::create_keg(&token, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_keg(token: String, keg_id: String, keg_data: api_client::KegUpdatePayload) -> Result<api_client::Keg, AppError> {
    info!("[COMMAND]     ID: {}", keg_id);
    api_client::update_keg(&token, &keg_id, &keg_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn delete_keg(token: String, keg_id: String) -> Result<(), AppError> {
    info!("[COMMAND]     ID: {}", keg_id);
    api_client::delete_keg(&token, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_taps(token: String) -> Result<Vec<api_client::Tap>, AppError> {
    info!("[COMMAND]     API...");
    api_client::get_taps(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_pours(token: String, limit: u32) -> Result<Vec<api_client::PourResponse>, AppError> {
    info!("[COMMAND]     API...");
    api_client::get_pours(&token, limit).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_beverages(token: String) -> Result<Vec<api_client::Beverage>, AppError> {
    info!("[COMMAND]     API...");
    api_client::get_beverages(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_beverage(token: String, beverage_data: api_client::BeveragePayload) -> Result<api_client::Beverage, AppError> {
    info!("[COMMAND]     ...");
    api_client::create_beverage(&token, &beverage_data).await.map_err(AppError::from)
}

#[tauri::command]
async fn assign_keg_to_tap(token: String, tap_id: i32, keg_id: String) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND]     ID: {}   ID: {}", keg_id, tap_id);
    api_client::assign_keg_to_tap(&token, tap_id, &keg_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn unassign_keg_from_tap(token: String, tap_id: i32) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND]       ID: {}", tap_id);
    api_client::unassign_keg_from_tap(&token, tap_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn update_tap(token: String, tap_id: i32, payload: api_client::TapUpdatePayload) -> Result<api_client::Tap, AppError> {
    info!("[COMMAND]     ID: {}", tap_id);
    api_client::update_tap(&token, tap_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_system_status(token: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND]   ...");
    api_client::get_system_status(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn set_emergency_stop(token: String, value: String) -> Result<api_client::SystemStateItem, AppError> {
    info!("[COMMAND]     Emergency Stop  '{}'", value);
    let payload = api_client::SystemStateUpdatePayload { value };
    api_client::set_emergency_stop(&token, &payload).await.map_err(AppError::from)
}



#[tauri::command]
async fn get_current_shift(token: String) -> Result<api_client::ShiftCurrentResponse, AppError> {
    info!("[COMMAND]   ...");
    api_client::get_current_shift(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn open_shift(token: String) -> Result<api_client::Shift, AppError> {
    info!("[COMMAND]    ...");
    api_client::open_shift(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn close_shift(token: String) -> Result<api_client::Shift, AppError> {
    info!("[COMMAND]    ...");
    api_client::close_shift(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_shift_x_report(token: String, shift_id: String) -> Result<api_client::ShiftReportPayload, AppError> {
    info!("[COMMAND]   X-report shift_id={}", shift_id);
    api_client::get_shift_x_report(&token, &shift_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn create_shift_z_report(token: String, shift_id: String) -> Result<api_client::ShiftReportDocument, AppError> {
    info!("[COMMAND]   create Z-report shift_id={}", shift_id);
    api_client::create_shift_z_report(&token, &shift_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn get_shift_z_report(token: String, shift_id: String) -> Result<api_client::ShiftReportDocument, AppError> {
    info!("[COMMAND]   get Z-report shift_id={}", shift_id);
    api_client::get_shift_z_report(&token, &shift_id).await.map_err(AppError::from)
}

#[tauri::command]
async fn list_shift_z_reports(
    token: String,
    from_date: String,
    to_date: String,
) -> Result<Vec<api_client::ShiftZReportListItem>, AppError> {
    info!("[COMMAND]   list Z-reports from={} to={}", from_date, to_date);
    api_client::list_shift_z_reports(&token, &from_date, &to_date).await.map_err(AppError::from)
}
#[tauri::command]
async fn get_active_visits(token: String) -> Result<Vec<api_client::VisitActiveListItem>, AppError> {
    info!("[COMMAND]    ...");
    api_client::get_active_visits(&token).await.map_err(AppError::from)
}

#[tauri::command]
async fn search_active_visit(token: String, query: String) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND]      ...");
    api_client::search_active_visit(&token, &query).await.map_err(AppError::from)
}

#[tauri::command]
async fn open_visit(token: String, guest_id: String, card_uid: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND]     ID: {}", guest_id);
    let payload = api_client::VisitOpenPayload { guest_id, card_uid };
    api_client::open_visit(&token, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn assign_card_to_visit(token: String, visit_id: String, card_uid: String) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND]     ID: {}", visit_id);
    let payload = api_client::VisitAssignCardPayload { card_uid };
    api_client::assign_card_to_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn force_unlock_visit(token: String, visit_id: String, reason: String, comment: Option<String>) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND] Force unlock   ID: {}", visit_id);
    let payload = api_client::VisitForceUnlockPayload { reason, comment };
    api_client::force_unlock_visit(&token, &visit_id, &payload).await.map_err(AppError::from)
}

#[tauri::command]
async fn close_visit(token: String, visit_id: String, closed_reason: String, card_returned: bool) -> Result<api_client::Visit, AppError> {
    info!("[COMMAND]   ID: {}", visit_id);
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

#[tauri::command]
async fn report_lost_card_from_visit(
    token: String,
    visit_id: String,
    reason: Option<String>,
    comment: Option<String>,
) -> Result<api_client::VisitReportLostCardResponse, AppError> {
    let payload = api_client::VisitReportLostCardPayload { reason, comment };
    api_client::report_lost_card_from_visit(&token, &visit_id, &payload)
        .await
        .map_err(AppError::from)
}

#[tauri::command]
async fn list_lost_cards(
    token: String,
    uid: Option<String>,
    reported_from: Option<String>,
    reported_to: Option<String>,
) -> Result<Vec<api_client::LostCard>, AppError> {
    api_client::list_lost_cards(
        &token,
        uid.as_deref(),
        reported_from.as_deref(),
        reported_to.as_deref(),
    )
    .await
    .map_err(AppError::from)
}

#[tauri::command]
async fn restore_lost_card(token: String, card_uid: String) -> Result<api_client::LostCardRestoreResponse, AppError> {
    api_client::restore_lost_card(&token, &card_uid).await.map_err(AppError::from)
}

// =============================================================================
//   
// =============================================================================

fn main() {
    // ... (panic_hook  PC/SC context  )
    let default_panic_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |panic_info| {
        error!("!!! THREAD PANICKED !!!: {}", panic_info);
        default_panic_hook(panic_info);
    }));

    let context = Arc::new(Mutex::new(Context::establish(Scope::User)
        .expect("   PC/SC ...")));

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
        // --- :      ---
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
            get_current_shift,
            open_shift,
            close_shift,
            get_shift_x_report,
            create_shift_z_report,
            get_shift_z_report,
            list_shift_z_reports,
            // API - Visits
            get_active_visits,
            search_active_visit,
            open_visit,
            assign_card_to_visit,
            force_unlock_visit,
            close_visit,
            reconcile_pour,
            report_lost_card_from_visit,
            list_lost_cards,
            restore_lost_card
        ])
        .setup(move |app| {
            // ... (  NFC  )
            let app_handle = app.handle().clone();
            let context_clone = Arc::clone(&context);
            
            info!("     ...");
            //      thread::spawn
            thread::spawn(move || {
                let mut last_payload_json = String::new(); //    

                loop {
                    let payload = match nfc_handler::list_readers_internal(&context_clone) {
                        // :      
                        Ok(mut names) if !names.is_empty() => {
                            let reader_name = names.remove(0);
                            //  .   .
                            match nfc_handler::get_card_uid_internal(&context_clone, &reader_name) {
                                Ok(uid_bytes) => {
                                    //  .
                                    CardStatusPayload { uid: Some(hex::encode(uid_bytes)), error: None }
                                },
                                Err(pcsc::Error::NoSmartcard) | Err(pcsc::Error::RemovedCard) => {
                                    //  ,    ( ).  , "" .
                                    CardStatusPayload { uid: None, error: None }
                                },
                                Err(e) => {
                                    //   PC/SC,   .
                                    error!("   ( ): {}", e);
                                    CardStatusPayload { uid: None, error: Some(e.to_string()) }
                                }
                            }
                        },
                        // +++  :  ,    ( ,  Rust )
                        Ok(_) => {
                            error!(":   ,   .");
                            CardStatusPayload { uid: None, error: Some("  .".to_string()) }
                        }
                        // :    -  PC/SC
                        Err(e) => {
                            //       .
                            error!("  PC/SC: {}", e);
                            CardStatusPayload { uid: None, error: Some("  .".to_string()) }
                        }
                    };
                    
                    //  ,    payload   .
                    match serde_json::to_string(&payload) {
                        Ok(current_payload_json) => {
                            if current_payload_json != last_payload_json {
                                info!(" NFC ,  : {}", current_payload_json);
                                if let Err(e) = app_handle.emit("card-status-changed", payload.clone()) { //  .clone()
                                    error!("    card-status-changed: {}", e);
                                }
                                last_payload_json = current_payload_json;
                            }
                        },
                        Err(e) => {
                            error!("   payload: {}", e);
                        }
                    }

                    thread::sleep(Duration::from_millis(500));
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("   Tauri ");
}



