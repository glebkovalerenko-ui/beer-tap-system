import { writable } from 'svelte/store';

import { getApiBaseUrl, initializeBackendBaseUrl } from './config.js';

export const authToken = writable(localStorage.getItem('authToken'));
export const isAuthenticated = writable(!!localStorage.getItem('authToken'));

authToken.subscribe((value) => {
  if (value) {
    localStorage.setItem('authToken', value);
    isAuthenticated.set(true);
  } else {
    localStorage.removeItem('authToken');
    isAuthenticated.set(false);
  }
});

export async function login(username, password) {
  await initializeBackendBaseUrl();

  const response = await fetch(`${getApiBaseUrl()}/api/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  authToken.set(data.access_token);
}

export function logout() {
  authToken.set(null);
}

export async function apiFetch(url, options = {}) {
  await initializeBackendBaseUrl();

  const token = localStorage.getItem('authToken');
  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(`${getApiBaseUrl()}${url}`, { ...options, headers });

  if (response.status === 401) {
    logout();
    throw new Error('Unauthorized');
  }
  if (!response.ok) {
    throw new Error('API request failed');
  }
  return response.json();
}
