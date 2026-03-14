import { get } from 'svelte/store';

import { getApiBaseUrl, initializeBackendBaseUrl } from './config.js';
import { normalizeError } from './errorUtils.js';
import { sessionStore } from '../stores/sessionStore.js';

const REAUTH_MESSAGE = 'Требуется повторный вход в систему';

function getAdminToken() {
  const storeToken = get(sessionStore).token;
  if (storeToken) {
    return storeToken;
  }

  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('jwt_token');
  }

  return null;
}

function resolveRequestUrl(pathOrUrl) {
  if (/^https?:\/\//i.test(pathOrUrl)) {
    return pathOrUrl;
  }

  const normalizedPath = String(pathOrUrl || '').startsWith('/')
    ? String(pathOrUrl)
    : `/${String(pathOrUrl || '')}`;

  return `${getApiBaseUrl()}${normalizedPath}`;
}

async function readErrorMessage(response) {
  const jsonResponse = response.clone();
  const textResponse = response.clone();
  const payload = await jsonResponse.json().catch(() => null);

  if (typeof payload?.detail === 'string' && payload.detail.trim()) {
    return payload.detail.trim();
  }

  if (typeof payload?.message === 'string' && payload.message.trim()) {
    return payload.message.trim();
  }

  if (payload?.detail) {
    return JSON.stringify(payload.detail);
  }

  const text = await textResponse.text().catch(() => '');
  if (text && text.trim()) {
    return text.trim();
  }

  if (response.status === 401) {
    return REAUTH_MESSAGE;
  }

  return `HTTP ${response.status}`;
}

async function request(pathOrUrl, { method = 'GET', headers = {}, body, responseType = 'json' } = {}) {
  await initializeBackendBaseUrl();

  const token = getAdminToken();
  if (!token) {
    throw new Error(REAUTH_MESSAGE);
  }

  const response = await fetch(resolveRequestUrl(pathOrUrl), {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...headers,
    },
    body,
  });

  if (!response.ok) {
    throw new Error(normalizeError(await readErrorMessage(response)));
  }

  if (responseType === 'blob') {
    return response.blob();
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function displayAdminGetJson(pathOrUrl) {
  return request(pathOrUrl);
}

export function displayAdminPutJson(pathOrUrl, payload) {
  return request(pathOrUrl, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function displayAdminPostMultipart(pathOrUrl, body) {
  return request(pathOrUrl, {
    method: 'POST',
    body,
  });
}

export function displayAdminFetchBlob(pathOrUrl) {
  return request(pathOrUrl, {
    responseType: 'blob',
  });
}

export function listDisplayMediaAssets(kind) {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : '';
  return displayAdminGetJson(`/api/media-assets${query}`);
}

export function uploadDisplayMediaAsset(kind, file) {
  const body = new FormData();
  body.set('kind', kind);
  body.set('file', file);
  return displayAdminPostMultipart('/api/media-assets', body);
}
