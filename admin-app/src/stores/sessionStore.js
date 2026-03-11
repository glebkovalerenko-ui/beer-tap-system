// src/stores/sessionStore.js
import { writable } from 'svelte/store';

function createSessionStore() {
  const { subscribe, set } = writable({
    token: localStorage.getItem('jwt_token') || null,
    user: null,
  });

  return {
    subscribe,
    setToken: (token) => {
      localStorage.setItem('jwt_token', token);
      set({ token, user: null });
    },
    logout: () => {
      localStorage.removeItem('jwt_token');
      set({ token: null, user: null });
    }
  };
}

export const sessionStore = createSessionStore();
