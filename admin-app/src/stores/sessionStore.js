// src/stores/sessionStore.js
import { writable } from 'svelte/store';

function createSessionStore() {
  const { subscribe, set } = writable({
    token: localStorage.getItem('jwt_token') || null, // Восстанавливаем токен при запуске
    user: null, // Здесь будет информация о пользователе
  });

  return {
    subscribe,
    setToken: (token) => {
      localStorage.setItem('jwt_token', token);
      set({ token, user: null }); // В будущем можно будет декодировать токен или запрашивать /api/users/me
    },
    logout: () => {
      localStorage.removeItem('jwt_token');
      set({ token: null, user: null });
    }
  };
}

export const sessionStore = createSessionStore();