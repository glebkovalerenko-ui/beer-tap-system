// src-tauri/src/api_client.rs

//! Модуль-клиент для взаимодействия с API бэкенда (FastAPI).
//! Инкапсулирует всю HTTP-логику, DTO (Data Transfer Objects) и обработку ошибок.

// +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем `Deserialize` в `use` для `TopUpPayload` +++
use serde::{Deserialize, Serialize};
// +++ КОНЕЦ ИЗМЕНЕНИЙ +++
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

// +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем `Deserialize` в макрос `derive` +++
// КОММЕНТАРИЙ: Это исправление критической ошибки компиляции. Tauri должен уметь
// "десериализовать" JSON, приходящий из frontend, в эту Rust-структуру.
#[derive(Serialize, Deserialize, Debug)]
// +++ КОНЕЦ ИЗМЕНЕНИЙ +++
pub struct TopUpPayload {
    pub amount: String, // Pydantic `Decimal` сериализуется в строку
    pub payment_method: String,
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

// --- Error Handling ---
#[derive(Deserialize)]
struct ApiErrorDetail {
    detail: String,
}

/// Вспомогательная функция для парсинга стандартных ошибок FastAPI.
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

/// Аутентификация пользователя и получение JWT токена.
pub async fn login(credentials: &LoginCredentials<'_>) -> Result<String, String> {
    let url = format!("{}/token", API_BASE_URL);
    let response = CLIENT.post(&url).form(credentials).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        let token_response = response.json::<TokenResponse>().await.map_err(|e| e.to_string())?;
        Ok(token_response.access_token)
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Получение списка всех гостей.
pub async fn get_guests(token: &str) -> Result<Vec<Guest>, String> {
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Guest>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Создание нового гостя.
pub async fn create_guest(token: &str, guest_data: &GuestPayload) -> Result<Guest, String> {
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Обновление данных существующего гостя.
pub async fn update_guest(token: &str, guest_id: &str, guest_data: &GuestUpdatePayload) -> Result<Guest, String> {
    let url = format!("{}/guests/{}", API_BASE_URL, guest_id);
    let response = CLIENT.put(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

/// Привязка карты к гостю (с логикой "найти или создать" на бэкенде).
pub async fn bind_card_to_guest(token: &str, guest_id: &str, card_uid: &str) -> Result<Guest, String> {
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

/// Пополнение баланса гостя.
pub async fn top_up_balance(token: &str, guest_id: &str, top_up_data: &TopUpPayload) -> Result<Guest, String> {
    let url = format!("{}/guests/{}/topup", API_BASE_URL, guest_id);

    let response = CLIENT.post(&url)
        .bearer_auth(token)
        .json(top_up_data)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if response.status().is_success() {
        // Ожидаем, что API вернет обновленный объект гостя с новым балансом.
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}