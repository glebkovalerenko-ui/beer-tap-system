// admin-app/src/stores/systemStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

const createSystemStore = () => {
  const { subscribe, update } = writable({
    emergencyStop: false,
    loading: false,
    error: null,
  });

  let pollingInterval = null;
  const POLLING_RATE_MS = 10000;

  const fetchSystemStatus = async () => {
    const token = get(sessionStore).token;
    if (!token) {
      console.warn('[SystemStore] No token found, skipping fetch.');
      return;
    }

    try {
      const statusItem = await invoke('get_system_status', { token });
      if (statusItem && statusItem.key === 'emergency_stop_enabled') {
        update((store) => ({ ...store, emergencyStop: statusItem.value === 'true', error: null }));
      }
    } catch (err) {
      const message = toErrorMessage('systemStore.fetchSystemStatus', err);
      update((store) => ({ ...store, error: message }));
    }
  };

  const setEmergencyStop = async (enabled) => {
    const token = get(sessionStore).token;
    if (!token) {
      const error = 'Authentication token not found.';
      update((store) => ({ ...store, error }));
      throw new Error(error);
    }

    update((store) => ({ ...store, loading: true }));
    try {
      const value = enabled ? 'true' : 'false';
      const updatedStatus = await invoke('set_emergency_stop', { token, value });
      if (updatedStatus && updatedStatus.key === 'emergency_stop_enabled') {
        update((store) => ({
          ...store,
          emergencyStop: updatedStatus.value === 'true',
          loading: false,
          error: null,
        }));
      }
    } catch (err) {
      const message = toErrorMessage('systemStore.setEmergencyStop', err);
      update((store) => ({ ...store, loading: false, error: message }));
      throw new Error(message);
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

  return {
    subscribe,
    setEmergencyStop,
    startPolling,
    stopPolling,
  };
};

export const systemStore = createSystemStore();
