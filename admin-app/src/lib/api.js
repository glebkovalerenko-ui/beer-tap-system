import { writable } from 'svelte/store';

// Svelte-стор для хранения токена и состояния аутентификации
export const authToken = writable(localStorage.getItem('authToken'));
export const isAuthenticated = writable(!!localStorage.getItem('authToken'));

// Базовый URL нашего API
const BASE_URL = 'http://localhost:8000'; // Убедитесь, что порт правильный

authToken.subscribe(value => {
    if (value) {
        localStorage.setItem('authToken', value);
        isAuthenticated.set(true);
    } else {
        localStorage.removeItem('authToken');
        isAuthenticated.set(false);
    }
});

// Функция для логина
export async function login(username, password) {
    const response = await fetch(`${BASE_URL}/api/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password })
    });

    if (!response.ok) {
        throw new Error('Login failed');
    }

    const data = await response.json();
    authToken.set(data.access_token);
}

// Функция для выхода
export function logout() {
    authToken.set(null);
}

// Обертка для всех защищенных запросов
export async function apiFetch(url, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
    };

    const response = await fetch(`${BASE_URL}${url}`, { ...options, headers });

    if (response.status === 401) {
        // Если токен протух или невалиден, разлогиниваем пользователя
        logout();
        throw new Error('Unauthorized');
    }
    if (!response.ok) {
        throw new Error('API request failed');
    }
    return response.json();
}