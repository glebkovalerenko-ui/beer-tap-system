import { invoke } from '@tauri-apps/api/core';

const DEFAULT_API_BASE_URL = 'http://cybeer-hub:8000';

function normalizeBaseUrl(value) {
  const normalized = String(value || '').trim().replace(/\/$/, '');
  return normalized || DEFAULT_API_BASE_URL;
}

function readWindowConfigBaseUrl() {
  if (typeof window === 'undefined') {
    return '';
  }

  const runtimeConfig = window.__APP_CONFIG__ || {};
  return (
    runtimeConfig.API_BASE_URL ||
    runtimeConfig.apiBaseUrl ||
    runtimeConfig.BACKEND_BASE_URL ||
    runtimeConfig.backendBaseUrl ||
    ''
  );
}

function resolveApiBaseUrl() {
  return normalizeBaseUrl(
    import.meta.env.VITE_API_BASE_URL ||
      import.meta.env.VITE_BACKEND_BASE_URL ||
      readWindowConfigBaseUrl()
  );
}

export const API_BASE_URL = resolveApiBaseUrl();
export const SHOW_API_BASE_URL =
  import.meta.env.DEV ||
  String(import.meta.env.VITE_SHOW_API_BASE_URL || '').toLowerCase() === 'true';
export const DEMO_MODE_ENABLED_BY_DEFAULT =
  String(import.meta.env.VITE_DEMO_MODE || '').toLowerCase() === 'true';

let loggedBaseUrl = false;
let tauriConfigured = false;
let tauriBridgeAttempted = false;

export function logBackendBaseUrlOnce() {
  if (!loggedBaseUrl) {
    console.info(`[config] API_BASE_URL=${API_BASE_URL}`);
    loggedBaseUrl = true;
  }

  return API_BASE_URL;
}

export async function initializeBackendBaseUrl() {
  logBackendBaseUrlOnce();

  if (tauriConfigured || tauriBridgeAttempted) {
    return API_BASE_URL;
  }

  tauriBridgeAttempted = true;

  try {
    await invoke('configure_backend_base_url', { baseUrl: API_BASE_URL });
    tauriConfigured = true;
  } catch (error) {
    const message =
      typeof error === 'object' && error && 'message' in error
        ? String(error.message)
        : String(error || '');
    if (message) {
      console.debug(`[config] Tauri backend base url bridge unavailable: ${message}`);
    }
  }

  return API_BASE_URL;
}
