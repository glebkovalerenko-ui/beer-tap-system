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
    pub card_uid: String,
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

// --- Error Handling ---
#[derive(Deserialize)]
struct ApiErrorDetail {
    detail: String,
}

async fn handle_api_error(response: Response) -> String {
    let status = response.status();
    if let Ok(error_body) = response.json::<ApiErrorDetail>().await {
        error_body.detail
    } else {
        format!("HTTP Error: {}", status)
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