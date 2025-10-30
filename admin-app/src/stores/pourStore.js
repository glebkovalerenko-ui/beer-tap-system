// src/stores/pourStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

const POLL_INTERVAL_MS = 10000; // Опрашивать каждые 10 секунд

function createPourStore() {
  let pollInterval = null;

  const { subscribe, set, update } = writable({
    pours: [],
    loading: false,
    error: null,
  });

  async function fetchPours() {
    const token = get(sessionStore).token;
    if (!token) {
      console.warn("fetchPours called without a token. Polling will not start.");
      return;
    }
    
    // Устанавливаем loading только при первой загрузке, чтобы избежать мигания UI
    update(s => {
        if (s.pours.length === 0) {
            return { ...s, loading: true, error: null };
        }
        return s;
    });

    try {
      const pours = await invoke('get_pours', { token, limit: 20 });
      set({ pours, loading: false, error: null });
    } catch (error) {
      const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
      update(s => ({ ...s, loading: false, error: errorMessage }));
      // Останавливаем опрос при ошибке, чтобы не спамить запросами
      stopPolling(); 
    }
  }

  function startPolling() {
    if (pollInterval) return; // Уже запущен
    console.log("Starting pours polling...");
    // Немедленно выполняем первый запрос, не дожидаясь интервала
    fetchPours();
    pollInterval = setInterval(fetchPours, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollInterval) {
      console.log("Stopping pours polling.");
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // Следим за состоянием сессии
  sessionStore.subscribe(session => {
    if (session.token) {
      startPolling();
    } else {
      stopPolling();
      // Очищаем данные при выходе из системы
      set({ pours: [], loading: false, error: null });
    }
  });

  return {
    subscribe,
    // Мы не экспортируем start/stop, так как стор сам управляет своим жизненным циклом
  };
}

export const pourStore = createPourStore();