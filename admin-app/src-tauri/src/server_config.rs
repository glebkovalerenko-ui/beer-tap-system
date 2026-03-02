use reqwest::{Client, Url};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;
use tauri::{AppHandle, Manager, Runtime};

pub const DEFAULT_SERVER_BASE_URL: &str = "http://cybeer-hub:8000";

const SERVER_CONFIG_FILE_NAME: &str = "server-config.json";
const SERVER_STATUS_PATH: &str = "/api/system/status";
const SERVER_CONNECTION_TIMEOUT_SECONDS: u64 = 5;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub base_url: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ServerConnectionTestResult {
    pub base_url: String,
    pub checked_url: String,
    pub status_code: u16,
}

fn trim_base_url(value: &str) -> String {
    value.trim().trim_end_matches('/').to_string()
}

pub fn validate_server_base_url(value: &str) -> Result<String, String> {
    let normalized = trim_base_url(value);
    if normalized.is_empty() {
        return Err("Server URL must not be empty.".to_string());
    }

    let parsed = Url::parse(&normalized)
        .map_err(|_| "Server URL must be a valid http:// or https:// URL.".to_string())?;

    match parsed.scheme() {
        "http" | "https" => {}
        _ => {
            return Err("Server URL must start with http:// or https://.".to_string());
        }
    }

    if parsed.host_str().is_none() {
        return Err("Server URL must include a host.".to_string());
    }

    Ok(normalized)
}

pub fn default_server_base_url() -> String {
    DEFAULT_SERVER_BASE_URL.to_string()
}

fn server_config_path<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    let config_dir = app
        .path()
        .app_config_dir()
        .map_err(|error| format!("Failed to resolve app config dir: {error}"))?;

    Ok(config_dir.join(SERVER_CONFIG_FILE_NAME))
}

pub fn load_server_base_url<R: Runtime>(app: &AppHandle<R>) -> Result<String, String> {
    let path = server_config_path(app)?;
    if !path.exists() {
        return Ok(default_server_base_url());
    }

    let contents = fs::read_to_string(&path)
        .map_err(|error| format!("Failed to read server config {}: {error}", path.display()))?;
    let config = serde_json::from_str::<ServerConfig>(&contents)
        .map_err(|error| format!("Failed to parse server config {}: {error}", path.display()))?;

    validate_server_base_url(&config.base_url)
}

pub fn persist_server_base_url<R: Runtime>(
    app: &AppHandle<R>,
    base_url: &str,
) -> Result<String, String> {
    let normalized = validate_server_base_url(base_url)?;
    let path = server_config_path(app)?;

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            format!(
                "Failed to create app config directory {}: {error}",
                parent.display()
            )
        })?;
    }

    let config = ServerConfig {
        base_url: normalized.clone(),
    };
    let serialized = serde_json::to_string_pretty(&config)
        .map_err(|error| format!("Failed to serialize server config: {error}"))?;

    fs::write(&path, serialized)
        .map_err(|error| format!("Failed to write server config {}: {error}", path.display()))?;

    Ok(normalized)
}

pub async fn test_server_connection(base_url: &str) -> Result<ServerConnectionTestResult, String> {
    let normalized = validate_server_base_url(base_url)?;
    let checked_url = format!("{normalized}{SERVER_STATUS_PATH}");
    let client = Client::builder()
        .timeout(Duration::from_secs(SERVER_CONNECTION_TIMEOUT_SECONDS))
        .build()
        .map_err(|error| format!("Failed to create HTTP client for server test: {error}"))?;

    let response = client
        .get(&checked_url)
        .send()
        .await
        .map_err(|error| format!("Server connection test failed for {checked_url}: {error}"))?;

    if !response.status().is_success() {
        return Err(format!(
            "Server connection test failed for {checked_url}: HTTP {}",
            response.status().as_u16()
        ));
    }

    Ok(ServerConnectionTestResult {
        base_url: normalized,
        checked_url,
        status_code: response.status().as_u16(),
    })
}
