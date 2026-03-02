import { invoke } from '@tauri-apps/api/core';

const DEFAULT_BACKEND_BASE_URL = 'http://cybeer-hub:8000';
const configuredBaseUrl = String(import.meta.env.VITE_BACKEND_BASE_URL || DEFAULT_BACKEND_BASE_URL).trim();

export const BACKEND_BASE_URL = configuredBaseUrl.replace(/\/$/, '');
export const API_BASE_URL = BACKEND_BASE_URL;
export const DEMO_MODE_ENABLED_BY_DEFAULT = String(import.meta.env.VITE_DEMO_MODE || '').toLowerCase() === 'true';

let loggedBaseUrl = false;
let tauriConfigured = false;
let tauriBridgeAttempted = false;

export function logBackendBaseUrlOnce() {
  if (loggedBaseUrl) {
    return BACKEND_BASE_URL;
  }

  console.info(`[config] backend base url = ${BACKEND_BASE_URL}`);
  loggedBaseUrl = true;
  return BACKEND_BASE_URL;
}

export async function initializeBackendBaseUrl() {
  logBackendBaseUrlOnce();

  if (tauriConfigured) {
    return BACKEND_BASE_URL;
  }

  if (tauriBridgeAttempted) {
    return BACKEND_BASE_URL;
  }

  tauriBridgeAttempted = true;

  try {
    await invoke('configure_backend_base_url', { baseUrl: BACKEND_BASE_URL });
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

  return BACKEND_BASE_URL;
}
