// admin-app/src/stores/systemStore.js
// --- ДЛЯ ПОЛНОЙ ЗАМЕНЫ ---

import { writable, get } from 'svelte/store'; // <-- ИЗМЕНЕНО: Импортируем 'get'
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';

const createSystemStore = () => {
  const { subscribe, set, update } = writable({
    emergencyStop: false,
    loading: false,
    error: null,
  });

  let pollingInterval = null;
  const POLLING_RATE_MS = 10000;

  const fetchSystemStatus = async () => {
    // --- ИЗМЕНЕНО: Получаем токен идиоматичным способом ---
    const token = get(sessionStore).token;
    if (!token) {
      console.warn('[SystemStore] No token found, skipping fetch.');
      return; 
    }

    try {
      const statusItem = await invoke('get_system_status', { token }); 
      if (statusItem && statusItem.key === 'emergency_stop_enabled') {
        update(store => ({ ...store, emergencyStop: statusItem.value === 'true', error: null }));
      }
    } catch (err) {
      console.error("Error fetching system status:", err);
      update(store => ({ ...store, error: err }));
    }
  };

  const setEmergencyStop = async (enabled) => {
    // --- ИЗМЕНЕНО: Получаем токен идиоматичным способом ---
    const token = get(sessionStore).token;
    if (!token) {
        const error = 'Authentication token not found.';
        update(store => ({ ...store, error }));
        throw new Error(error);
    }

    update(store => ({ ...store, loading: true }));
    try {
      const value = enabled ? 'true' : 'false';
      // Передаем токен в Tauri-команду
      const updatedStatus = await invoke('set_emergency_stop', { token, value });
      if (updatedStatus && updatedStatus.key === 'emergency_stop_enabled') {
         update(store => ({
          ...store,
          emergencyStop: updatedStatus.value === 'true',
          loading: false,
          error: null
        }));
      }
    } catch (err) {
      console.error("Error setting emergency stop:", err);
      update(store => ({ ...store, loading: false, error: err }));
      throw err;
    }
  };
  
  const startPolling = () => {
    if (pollingInterval) return;
    console.log('[SystemStore] Starting status polling.');
    fetchSystemStatus();
    pollingInterval = setInterval(fetchSystemStatus, POLLING_RATE_MS);
  };

  const stopPolling = () => {
    if (!pollingInterval) return;
    console.log('[SystemStore] Stopping status polling.');
    clearInterval(pollingInterval);
    pollingInterval = null;
  };
  
  // --- ИЗМЕНЕНО: Убираем автоматическую подписку ---
  // Теперь родительский компонент (App.svelte) будет отвечать за запуск/остановку.

  return {
    subscribe,
    setEmergencyStop,
    startPolling, // <-- Экспортируем методы
    stopPolling,  // <-- Экспортируем методы
  };
};

export const systemStore = createSystemStore();