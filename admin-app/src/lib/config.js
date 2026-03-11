import { invoke } from '@tauri-apps/api/core';
import { get, writable } from 'svelte/store';

const DEFAULT_API_BASE_URL = 'http://cybeer-hub:8000';

function normalizeBaseUrl(value, fallback = '') {
  const normalized = String(value || '').trim().replace(/\/+$/, '');
  return normalized || fallback;
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

function resolveBuildTimeBaseUrl() {
  return normalizeBaseUrl(
    import.meta.env.VITE_API_BASE_URL ||
      import.meta.env.VITE_BACKEND_BASE_URL ||
      readWindowConfigBaseUrl(),
    DEFAULT_API_BASE_URL
  );
}

function validateBaseUrl(value) {
  const normalized = normalizeBaseUrl(value);
  if (!normalized) {
    throw new Error('Адрес сервера не должен быть пустым.');
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(normalized);
  } catch {
    throw new Error('Адрес сервера должен быть корректным URL с http:// или https://.');
  }

  if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
    throw new Error('Адрес сервера должен начинаться с http:// или https://.');
  }

  if (!parsedUrl.host) {
    throw new Error('Адрес сервера должен содержать имя узла.');
  }

  return normalizeBaseUrl(parsedUrl.toString());
}

const initialBaseUrl = resolveBuildTimeBaseUrl();
let currentApiBaseUrl = initialBaseUrl;
let loggedBaseUrl = false;
let initialized = false;
let initializationPromise = null;

const internalServerConfigStore = writable({
  baseUrl: initialBaseUrl,
  initialized: false,
  runtimeConfigAvailable: false,
  source: 'build-config',
});

internalServerConfigStore.subscribe((state) => {
  currentApiBaseUrl = state.baseUrl;
});

function setServerConfigState(nextState) {
  internalServerConfigStore.set(nextState);
}

function logBackendBaseUrlOnce(url = currentApiBaseUrl) {
  if (!loggedBaseUrl) {
    console.info(`[config] API_BASE_URL=${url}`);
    loggedBaseUrl = true;
  }

  return url;
}

function logTauriBridgeUnavailable(error) {
  const message =
    typeof error === 'object' && error && 'message' in error
      ? String(error.message)
      : String(error || '');

  if (message) {
    console.debug(`[config] команды настройки адреса сервера недоступны: ${message}`);
  }
}

function runtimeConfigUnavailableError() {
  return new Error(
    'Изменение адреса сервера доступно только в настольном приложении Tauri. Для web/dev используйте VITE_API_BASE_URL.'
  );
}

export const serverConfigStore = {
  subscribe: internalServerConfigStore.subscribe,
};

export const SHOW_API_BASE_URL =
  import.meta.env.DEV ||
  String(import.meta.env.VITE_SHOW_API_BASE_URL || '').toLowerCase() === 'true';

export const DEMO_MODE_ENABLED_BY_DEFAULT =
  String(import.meta.env.VITE_DEMO_MODE || '').toLowerCase() === 'true';

export function getApiBaseUrl() {
  return currentApiBaseUrl;
}

export function validateApiBaseUrl(value) {
  return validateBaseUrl(value);
}

export async function initializeBackendBaseUrl() {
  if (initialized) {
    return currentApiBaseUrl;
  }

  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = (async () => {
    const buildBaseUrl = resolveBuildTimeBaseUrl();

    try {
      const runtimeBaseUrl = normalizeBaseUrl(await invoke('get_server_base_url'), buildBaseUrl);
      setServerConfigState({
        baseUrl: runtimeBaseUrl,
        initialized: true,
        runtimeConfigAvailable: true,
        source: 'runtime-config',
      });
      initialized = true;
      logBackendBaseUrlOnce(runtimeBaseUrl);
      return runtimeBaseUrl;
    } catch (error) {
      logTauriBridgeUnavailable(error);
      setServerConfigState({
        baseUrl: buildBaseUrl,
        initialized: true,
        runtimeConfigAvailable: false,
        source: 'build-config',
      });
      initialized = true;
      logBackendBaseUrlOnce(buildBaseUrl);
      return buildBaseUrl;
    }
  })();

  try {
    return await initializationPromise;
  } finally {
    initializationPromise = null;
  }
}

async function ensureRuntimeServerConfigAvailable() {
  await initializeBackendBaseUrl();

  if (!get(serverConfigStore).runtimeConfigAvailable) {
    throw runtimeConfigUnavailableError();
  }
}

export async function setServerBaseUrl(baseUrl) {
  await ensureRuntimeServerConfigAvailable();

  const normalized = validateBaseUrl(baseUrl);
  const savedBaseUrl = normalizeBaseUrl(
    await invoke('set_server_base_url', { baseUrl: normalized }),
    normalized
  );

  setServerConfigState({
    baseUrl: savedBaseUrl,
    initialized: true,
    runtimeConfigAvailable: true,
    source: 'runtime-config',
  });
  console.info(`[config] API_BASE_URL=${savedBaseUrl}`);
  return savedBaseUrl;
}

export async function testServerConnection(baseUrl) {
  await ensureRuntimeServerConfigAvailable();

  const normalized = validateBaseUrl(baseUrl ?? currentApiBaseUrl);
  return invoke('test_server_connection', { baseUrl: normalized });
}
