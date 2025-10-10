// src/api.js
import axios from 'axios';

// Эта сложная конструкция с VITE_API_BASE_URL больше не нужна,
// так как Nginx все делает за нас.

export const apiClient = axios.create({
  // Все запросы (например, /api/guests) будут отправляться
  // на тот же домен, где находится сайт. Nginx их поймает.
  baseURL: '/',
  headers: { 'Content-Type': 'application/json' }
});