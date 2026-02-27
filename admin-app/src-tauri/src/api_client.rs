// src-tauri/src/api_client.rs

//! Модуль-клиент для взаимодействия с API бэкенда (FastAPI).
//! Инкапсулирует всю HTTP-логику, DTO (Data Transfer Objects) и обработку ошибок.

use serde::{Deserialize, Serialize};
use reqwest::{Client, Response};
use once_cell::sync::Lazy;

// --- Лучшая практика: Единый, статичный HTTP-клиент с пулом соединений ---
static CLIENT: Lazy<Client> = Lazy::new(Client::new);

// --- Константы ---
const API_BASE_URL: &str = "http://localhost:8000/api";


// =============================================================================
// DTOs (Data Transfer Objects)
// КОММЕНТАРИЙ: Эти структуры точно соответствуют `schemas.py` на бэкенде.
// =============================================================================

// --- Auth ---
#[derive(Serialize)]
pub struct LoginCredentials<'a> {
    pub username: &'a str,
    pub password: &'a str,
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: String,
}

// --- Cards ---
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Card {
    pub card_uid: Option<String>,
    pub status: String,
    pub guest_id: Option<String>,
    pub created_at: String,
}

#[derive(Serialize, Debug)]
pub struct BindCardPayload<'a> {
    pub card_uid: &'a str,
}

// --- Transactions & Pours ---
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Transaction {
    pub transaction_id: String,
    pub amount: String,
    pub r#type: String, // `r#` используется, т.к. `type` - ключевое слово в Rust
    pub created_at: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Pour {
    pub pour_id: String,
    pub volume_ml: i32,
    pub amount_charged: String,
    pub poured_at: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TopUpPayload {
    pub amount: String, // Pydantic `Decimal` сериализуется в строку
    pub payment_method: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct PourGuest {
    pub guest_id: String,
    pub last_name: String,
    pub first_name: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct PourResponse {
    // Поля из `Pour`
    pub pour_id: String,
    pub volume_ml: i32,
    pub amount_charged: String,
    pub poured_at: String,
    // Вложенные структуры для UI
    pub guest: PourGuest,
    pub beverage: Beverage,
    pub tap: Tap,
}

// --- Guests ---
#[derive(Debug, Deserialize, Serialize, Clone)] 
pub struct Guest {
    pub guest_id: String,
    pub last_name: String,
    pub first_name: String,
    pub patronymic: Option<String>,
    pub phone_number: String,
    pub date_of_birth: String,
    pub id_document: String,
    pub balance: String,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
    pub cards: Vec<Card>,
    pub transactions: Vec<Transaction>,
    pub pours: Vec<Pour>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct GuestPayload {
    pub last_name: String,
    pub first_name: String,
    pub patronymic: Option<String>,
    pub phone_number: String,
    pub date_of_birth: String,
    pub id_document: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct GuestUpdatePayload {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub first_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub patronymic: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phone_number: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub date_of_birth: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id_document: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_active: Option<bool>,
}




#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct VisitGuest {
    pub guest_id: String,
    pub last_name: String,
    pub first_name: String,
    pub patronymic: Option<String>,
    pub phone_number: String,
    pub balance: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Visit {
    pub visit_id: String,
    pub guest_id: String,
    pub card_uid: Option<String>,
    pub status: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
    pub closed_reason: Option<String>,
    pub active_tap_id: Option<i32>,
    pub lock_set_at: Option<String>,
    pub card_returned: bool,
    pub guest: Option<VisitGuest>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitClosePayload {
    pub closed_reason: String,
    pub card_returned: bool,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitForceUnlockPayload {
    pub reason: String,
    pub comment: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitOpenPayload {
    pub guest_id: String,
    pub card_uid: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct VisitActiveListItem {
    pub visit_id: String,
    pub guest_id: String,
    pub guest_full_name: String,
    pub phone_number: String,
    pub balance: String,
    pub status: String,
    pub card_uid: Option<String>,
    pub active_tap_id: Option<i32>,
    pub lock_set_at: Option<String>,
    pub opened_at: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitAssignCardPayload {
    pub card_uid: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitReconcilePourPayload {
    pub tap_id: i32,
    pub short_id: String,
    pub volume_ml: i32,
    pub amount: String,
    pub reason: String,
    pub comment: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VisitReportLostCardPayload {
    pub reason: Option<String>,
    pub comment: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct LostCard {
    pub id: String,
    pub card_uid: String,
    pub reported_at: String,
    pub reported_by: Option<String>,
    pub reason: Option<String>,
    pub comment: Option<String>,
    pub visit_id: Option<String>,
    pub guest_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct VisitReportLostCardResponse {
    pub visit: Visit,
    pub lost_card: LostCard,
    pub lost: bool,
    pub already_marked: bool,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct LostCardCreatePayload {
    pub card_uid: String,
    pub reported_by: Option<String>,
    pub reason: Option<String>,
    pub comment: Option<String>,
    pub visit_id: Option<String>,
    pub guest_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct LostCardRestoreResponse {
    pub card_uid: String,
    pub restored: bool,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CardResolveLostCard {
    pub reported_at: String,
    pub comment: Option<String>,
    pub visit_id: Option<String>,
    pub reported_by: Option<String>,
    pub reason: Option<String>,
    pub guest_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CardResolveActiveVisit {
    pub visit_id: String,
    pub guest_id: String,
    pub guest_full_name: String,
    pub phone_number: String,
    pub status: String,
    pub card_uid: Option<String>,
    pub active_tap_id: Option<i32>,
    pub opened_at: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CardResolveGuest {
    pub guest_id: String,
    pub full_name: String,
    pub phone_number: String,
    pub balance_cents: i64,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CardResolveCard {
    pub uid: String,
    pub status: String,
    pub guest_id: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct CardResolveResponse {
    pub card_uid: String,
    pub is_lost: bool,
    pub lost_card: Option<CardResolveLostCard>,
    pub active_visit: Option<CardResolveActiveVisit>,
    pub guest: Option<CardResolveGuest>,
    pub card: Option<CardResolveCard>,
    pub recommended_action: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Shift {
    pub id: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
    pub status: String,
    pub opened_by: Option<String>,
    pub closed_by: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftCurrentResponse {
    pub status: String,
    pub shift: Option<Shift>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportMeta {
    pub shift_id: String,
    pub report_type: String,
    pub generated_at: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportTotals {
    pub pours_count: i32,
    pub total_volume_ml: i32,
    pub total_amount_cents: i32,
    pub new_guests_count: i32,
    pub pending_sync_count: i32,
    pub reconciled_count: i32,
    pub mismatch_count: i32,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportByTapItem {
    pub tap_id: i32,
    pub pours_count: i32,
    pub volume_ml: i32,
    pub amount_cents: i32,
    pub pending_sync_count: i32,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportVisits {
    pub active_visits_count: i32,
    pub closed_visits_count: i32,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportKegs {
    pub status: String,
    pub note: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportPayload {
    pub meta: ShiftReportMeta,
    pub totals: ShiftReportTotals,
    pub by_tap: Vec<ShiftReportByTapItem>,
    pub visits: ShiftReportVisits,
    pub kegs: ShiftReportKegs,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftReportDocument {
    pub report_id: String,
    pub shift_id: String,
    pub report_type: String,
    pub generated_at: String,
    pub payload: ShiftReportPayload,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ShiftZReportListItem {
    pub report_id: String,
    pub shift_id: String,
    pub generated_at: String,
    pub total_volume_ml: i32,
    pub total_amount_cents: i32,
    pub pours_count: i32,
    pub active_visits_count: i32,
    pub closed_visits_count: i32,
}

// --- Kegs, Taps, Beverages ---

// --- ИЗМЕНЕНИЕ: Структура Beverage расширена до полного соответствия схеме API ---
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Beverage {
    pub beverage_id: String,
    pub name: String,
    pub style: Option<String>,
    pub brewery: Option<String>,
    pub abv: Option<String>, // Decimal преобразуется в String
    // ВАЖНО: имя поля sell_price_per_liter точно соответствует Pydantic схеме
    pub sell_price_per_liter: String,
}

// --- ИЗМЕНЕНИЕ: Структура BeveragePayload приведена в полное соответствие с BeverageCreate ---
#[derive(Serialize, Deserialize, Debug)]
pub struct BeveragePayload {
    pub name: String,
    // ВАЖНО: имя поля style точно соответствует Pydantic схеме
    pub style: Option<String>,
    // ВАЖНО: имя поля brewery точно соответствует Pydantic схеме
    pub brewery: Option<String>,
    pub abv: Option<String>,
    // ВАЖНО: имя поля sell_price_per_liter точно соответствует Pydantic схеме
    pub sell_price_per_liter: String,
    // Поле description убрано, так как его нет в Pydantic схеме BeverageCreate
}


#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Keg {
    pub keg_id: String,
    pub initial_volume_ml: i32,
    pub current_volume_ml: i32,
    pub purchase_price: String,
    pub status: String, // e.g., 'new', 'in_use', 'empty'
    pub created_at: String,
    pub tapped_at: Option<String>,
    pub finished_at: Option<String>,
    pub beverage: Beverage, // Вложенная структура
}

#[derive(Serialize, Deserialize, Debug)]
pub struct KegPayload {
    pub beverage_id: String,
    pub initial_volume_ml: i32,
    pub purchase_price: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct KegUpdatePayload {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Tap {
    pub tap_id: i32,
    pub display_name: String,
    pub status: String, // e.g., 'active', 'locked', 'maintenance'
    pub keg_id: Option<String>,
    pub keg: Option<Keg>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TapUpdatePayload {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub display_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AssignKegPayload {
    pub keg_id: String,
}

// --- System State ---
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct SystemStateItem {
    pub key: String,
    pub value: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct SystemStateUpdatePayload {
    pub value: String,
}

// --- Error Handling ---
#[derive(Deserialize)]
#[serde(untagged)]
enum ApiDetail {
    Message(String),
    Conflict { message: String, visit_id: Option<String> },
}

#[derive(Deserialize)]
struct ApiErrorDetail {
    detail: ApiDetail,
}

fn ensure_non_empty_message(message: String, fallback: &str) -> String {
    let trimmed = message.trim();
    if trimmed.is_empty() {
        fallback.to_string()
    } else {
        trimmed.to_string()
    }
}

async fn handle_api_error(response: Response) -> String {
    let status = response.status();
    let endpoint = response.url().path().to_string();
    let fallback = format!("HTTP {} {}", status.as_u16(), endpoint);
    if let Ok(error_body) = response.json::<ApiErrorDetail>().await {
        let message = match error_body.detail {
            ApiDetail::Message(detail) => detail,
            ApiDetail::Conflict { message, visit_id } => match visit_id {
                Some(id) => format!("{} (visit_id={})", message, id),
                None => message,
            },
        };
        ensure_non_empty_message(message, &fallback)
    } else {
        fallback
    }
}

// =============================================================================
// ПУБЛИЧНЫЕ ФУНКЦИИ API
// =============================================================================

// --- Auth Functions ---
pub async fn login(credentials: &LoginCredentials<'_>) -> Result<String, String> {
    // ... (без изменений)
    let url = format!("{}/token", API_BASE_URL);
    let response = CLIENT.post(&url).form(credentials).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        let token_response = response.json::<TokenResponse>().await.map_err(|e| e.to_string())?;
        Ok(token_response.access_token)
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Guest Functions ---
pub async fn get_guests(token: &str) -> Result<Vec<Guest>, String> {
    // ... (без изменений)
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Guest>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn create_guest(token: &str, guest_data: &GuestPayload) -> Result<Guest, String> {
    // ... (без изменений)
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn update_guest(token: &str, guest_id: &str, guest_data: &GuestUpdatePayload) -> Result<Guest, String> {
    // ... (без изменений)
    let url = format!("{}/guests/{}", API_BASE_URL, guest_id);
    let response = CLIENT.put(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Card & Transaction Functions ---
pub async fn bind_card_to_guest(token: &str, guest_id: &str, card_uid: &str) -> Result<Guest, String> {
    // ... (без изменений)
    let url = format!("{}/guests/{}/cards", API_BASE_URL, guest_id);
    let payload = BindCardPayload { card_uid };

    let response = CLIENT.post(&url)
        .bearer_auth(token)
        .json(&payload)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn top_up_balance(token: &str, guest_id: &str, top_up_data: &TopUpPayload) -> Result<Guest, String> {
    // ... (без изменений)
    let url = format!("{}/guests/{}/topup", API_BASE_URL, guest_id);

    let response = CLIENT.post(&url)
        .bearer_auth(token)
        .json(top_up_data)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Keg Functions ---
pub async fn get_kegs(token: &str) -> Result<Vec<Keg>, String> {
    // ... (без изменений)
    let url = format!("{}/kegs/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Keg>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn create_keg(token: &str, keg_data: &KegPayload) -> Result<Keg, String> {
    // ... (без изменений)
    let url = format!("{}/kegs/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(keg_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Keg>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn update_keg(token: &str, keg_id: &str, keg_data: &KegUpdatePayload) -> Result<Keg, String> {
    // ... (без изменений)
    let url = format!("{}/kegs/{}", API_BASE_URL, keg_id);
    let response = CLIENT.put(&url).bearer_auth(token).json(keg_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Keg>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn delete_keg(token: &str, keg_id: &str) -> Result<(), String> {
    // ... (без изменений)
    let url = format!("{}/kegs/{}", API_BASE_URL, keg_id);
    let response = CLIENT.delete(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        Ok(())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Tap Functions ---
pub async fn get_taps(token: &str) -> Result<Vec<Tap>, String> {
    // ... (без изменений)
    let url = format!("{}/taps/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Tap>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Pour Functions ---
/// Получение списка последних наливов.
pub async fn get_pours(token: &str, limit: u32) -> Result<Vec<PourResponse>, String> {
    let url = format!("{}/pours/?limit={}", API_BASE_URL, limit);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<PourResponse>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Beverage Functions ---
/// Получение списка всех напитков.
pub async fn get_beverages(token: &str) -> Result<Vec<Beverage>, String> {
    let url = format!("{}/beverages/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Beverage>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Назначение кеги на кран.
pub async fn assign_keg_to_tap(token: &str, tap_id: i32, keg_id: &str) -> Result<Tap, String> {
    let url = format!("{}/taps/{}/keg", API_BASE_URL, tap_id);
    let payload = AssignKegPayload { keg_id: keg_id.to_string() };
    let response = CLIENT.put(&url).bearer_auth(token).json(&payload).send().await.map_err(|e| e.to_string())?;
    
    if response.status().is_success() {
        // Ожидаем, что API вернет обновленный объект крана
        response.json::<Tap>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Снятие кеги с крана.
pub async fn unassign_keg_from_tap(token: &str, tap_id: i32) -> Result<Tap, String> {
    let url = format!("{}/taps/{}/keg", API_BASE_URL, tap_id);
    let response = CLIENT.delete(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Tap>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Обновление статуса крана.
pub async fn update_tap(token: &str, tap_id: i32, payload: &TapUpdatePayload) -> Result<Tap, String> {
    let url = format!("{}/taps/{}", API_BASE_URL, tap_id);
    let response = CLIENT.put(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Tap>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Создание нового напитка.
pub async fn create_beverage(token: &str, beverage_data: &BeveragePayload) -> Result<Beverage, String> {
    let url = format!("{}/beverages/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(beverage_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Beverage>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- System Functions ---
/// Получение статуса экстренной остановки.
pub async fn get_system_status(token: &str) -> Result<SystemStateItem, String> {
    let url = format!("{}/system/status", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<SystemStateItem>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Установка статуса экстренной остановки.
pub async fn set_emergency_stop(token: &str, payload: &SystemStateUpdatePayload) -> Result<SystemStateItem, String> {
    let url = format!("{}/system/emergency_stop", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<SystemStateItem>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn get_current_shift(token: &str) -> Result<ShiftCurrentResponse, String> {
    let url = format!("{}/shifts/current", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<ShiftCurrentResponse>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn open_shift(token: &str) -> Result<Shift, String> {
    let url = format!("{}/shifts/open", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Shift>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn close_shift(token: &str) -> Result<Shift, String> {
    let url = format!("{}/shifts/close", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Shift>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn get_shift_x_report(token: &str, shift_id: &str) -> Result<ShiftReportPayload, String> {
    let url = format!("{}/shifts/{}/reports/x", API_BASE_URL, shift_id);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<ShiftReportPayload>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn create_shift_z_report(token: &str, shift_id: &str) -> Result<ShiftReportDocument, String> {
    let url = format!("{}/shifts/{}/reports/z", API_BASE_URL, shift_id);
    let response = CLIENT.post(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<ShiftReportDocument>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn get_shift_z_report(token: &str, shift_id: &str) -> Result<ShiftReportDocument, String> {
    let url = format!("{}/shifts/{}/reports/z", API_BASE_URL, shift_id);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<ShiftReportDocument>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn list_shift_z_reports(token: &str, from_date: &str, to_date: &str) -> Result<Vec<ShiftZReportListItem>, String> {
    let url = format!("{}/shifts/reports/z", API_BASE_URL);
    let response = CLIENT.get(&url)
        .query(&[("from", from_date), ("to", to_date)])
        .bearer_auth(token)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<ShiftZReportListItem>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// --- Visit Functions ---
pub async fn get_active_visits(token: &str) -> Result<Vec<VisitActiveListItem>, String> {
    let url = format!("{}/visits/active", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<VisitActiveListItem>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn search_active_visit(token: &str, query: &str) -> Result<Visit, String> {
    let url = format!("{}/visits/active/search", API_BASE_URL);
    let response = CLIENT.get(&url).query(&[("q", query)]).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn open_visit(token: &str, payload: &VisitOpenPayload) -> Result<Visit, String> {
    let url = format!("{}/visits/open", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn assign_card_to_visit(token: &str, visit_id: &str, payload: &VisitAssignCardPayload) -> Result<Visit, String> {
    let url = format!("{}/visits/{}/assign-card", API_BASE_URL, visit_id);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn force_unlock_visit(token: &str, visit_id: &str, payload: &VisitForceUnlockPayload) -> Result<Visit, String> {
    let url = format!("{}/visits/{}/force-unlock", API_BASE_URL, visit_id);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn close_visit(token: &str, visit_id: &str, payload: &VisitClosePayload) -> Result<Visit, String> {
    let url = format!("{}/visits/{}/close", API_BASE_URL, visit_id);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn reconcile_pour(token: &str, visit_id: &str, payload: &VisitReconcilePourPayload) -> Result<Visit, String> {
    let url = format!("{}/visits/{}/reconcile-pour", API_BASE_URL, visit_id);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Visit>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn report_lost_card_from_visit(
    token: &str,
    visit_id: &str,
    payload: &VisitReportLostCardPayload,
) -> Result<VisitReportLostCardResponse, String> {
    let url = format!("{}/visits/{}/report-lost-card", API_BASE_URL, visit_id);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response
            .json::<VisitReportLostCardResponse>()
            .await
            .map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn create_lost_card(token: &str, payload: &LostCardCreatePayload) -> Result<LostCard, String> {
    let url = format!("{}/lost-cards/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(payload).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<LostCard>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn list_lost_cards(
    token: &str,
    uid: Option<&str>,
    reported_from: Option<&str>,
    reported_to: Option<&str>,
) -> Result<Vec<LostCard>, String> {
    let url = format!("{}/lost-cards/", API_BASE_URL);
    let mut req = CLIENT.get(&url).bearer_auth(token);
    let mut params: Vec<(&str, &str)> = Vec::new();
    if let Some(value) = uid {
        if !value.trim().is_empty() {
            params.push(("uid", value));
        }
    }
    if let Some(value) = reported_from {
        if !value.trim().is_empty() {
            params.push(("reported_from", value));
        }
    }
    if let Some(value) = reported_to {
        if !value.trim().is_empty() {
            params.push(("reported_to", value));
        }
    }
    if !params.is_empty() {
        req = req.query(&params);
    }
    let response = req.send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<LostCard>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn restore_lost_card(token: &str, card_uid: &str) -> Result<LostCardRestoreResponse, String> {
    let url = format!("{}/lost-cards/{}/restore", API_BASE_URL, card_uid);
    let response = CLIENT.post(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response
            .json::<LostCardRestoreResponse>()
            .await
            .map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn resolve_card(token: &str, card_uid: &str) -> Result<CardResolveResponse, String> {
    let url = format!("{}/cards/{}/resolve", API_BASE_URL, card_uid);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response
            .json::<CardResolveResponse>()
            .await
            .map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}
