// src-tauri/src/api_client.rs

use serde::{Deserialize, Serialize};
use reqwest::{Client, Response};
use once_cell::sync::Lazy;

// --- Лучшая практика: Единый, статичный HTTP-клиент ---
static CLIENT: Lazy<Client> = Lazy::new(Client::new);

// --- Константы для URL ---
const API_BASE_URL: &str = "http://localhost:8000/api";

// --- Структуры данных (DTOs) ---
// (Существующие структуры без изменений)

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Transaction {
    pub transaction_id: String,
    pub amount: String,
    pub r#type: String, 
    pub created_at: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Pour {
    pub pour_id: String,
    pub volume_ml: i32,
    pub amount_charged: String,
    pub poured_at: String,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Card {
    pub card_uid: String,
    pub status: String,
    pub guest_id: Option<String>,
    pub created_at: String,
}

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

#[derive(Serialize)]
pub struct LoginCredentials<'a> {
    pub username: &'a str,
    pub password: &'a str,
}

#[derive(Deserialize)]
struct TokenResponse {
    access_token: String,
}

#[derive(Deserialize)]
struct ApiErrorDetail {
    detail: String,
}

// +++ НАЧАЛО ИЗМЕНЕНИЙ: Новая структура для тела запроса привязки карты +++
#[derive(Serialize, Debug)]
pub struct BindCardPayload<'a> {
    pub card_uid: &'a str,
}
// +++ КОНЕЦ ИЗМЕНЕНИЙ +++


// --- Вспомогательная функция для обработки ошибок API (без изменений) ---
async fn handle_api_error(response: Response) -> String {
    let status = response.status();
    if let Ok(error_body) = response.json::<ApiErrorDetail>().await {
        error_body.detail
    } else {
        format!("Error: {}", status)
    }
}

// --- Публичные функции API ---
// (Существующие функции без изменений)
pub async fn get_guests(token: &str) -> Result<Vec<Guest>, String> {
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.get(&url).bearer_auth(token).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Vec<Guest>>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

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

pub async fn create_guest(token: &str, guest_data: &GuestPayload) -> Result<Guest, String> {
    let url = format!("{}/guests/", API_BASE_URL);
    let response = CLIENT.post(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

pub async fn update_guest(token: &str, guest_id: &str, guest_data: &GuestUpdatePayload) -> Result<Guest, String> {
    let url = format!("{}/guests/{}", API_BASE_URL, guest_id);
    let response = CLIENT.put(&url).bearer_auth(token).json(guest_data).send().await.map_err(|e| e.to_string())?;
    if response.status().is_success() {
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}

// +++ НАЧАЛО ИЗМЕНЕНИЙ: Новая функция для привязки карты к гостю +++
// КОММЕНТАРИЙ: Эта функция будет вызывать эндпоинт `POST /api/guests/{guest_id}/cards`,
// который, как мы ожидаем, будет создан на бэкенде.
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
        // Ожидаем, что API вернет обновленный объект гостя со всеми его картами.
        response.json::<Guest>().await.map_err(|e| e.to_string())
    } else {
        Err(handle_api_error(response).await)
    }
}
// +++ КОНЕЦ ИЗМЕНЕНИЙ +++