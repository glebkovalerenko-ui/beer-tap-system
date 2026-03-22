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
    overallState: 'ok',
    generatedAt: null,
    openIncidentCount: 0,
    subsystems: [],
    loading: false,
    error: null,
  });

  let pollingInterval = null;
  const POLLING_RATE_MS = 10000;

  const applySummary = (summary) => update((store) => ({
    ...store,
    emergencyStop: Boolean(summary?.emergency_stop),
    overallState: summary?.overall_state || 'ok',
    generatedAt: summary?.generated_at || null,
    openIncidentCount: summary?.open_incident_count || 0,
    subsystems: summary?.subsystems || [],
    loading: false,
    error: null,
  }));

  const fetchSystemStatus = async () => {
    const token = get(sessionStore).token;
    if (!token) return;
    try {
      const summary = await invoke('get_system_status', { token });
      applySummary(summary);
    } catch (err) {
      const message = toErrorMessage('systemStore.fetchSystemStatus', err);
      update((store) => ({ ...store, loading: false, error: message }));
    }
  };

  const setEmergencyStop = async (enabled) => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    update((store) => ({ ...store, loading: true }));
    try {
      const summary = await invoke('set_emergency_stop', { token, value: enabled ? 'true' : 'false' });
      applySummary(summary);
    } catch (err) {
      const message = toErrorMessage('systemStore.setEmergencyStop', err);
      update((store) => ({ ...store, loading: false, error: message }));
      throw new Error(message);
    }
  };

  const startPolling = () => {
    if (pollingInterval) return;
    fetchSystemStatus();
    pollingInterval = setInterval(fetchSystemStatus, POLLING_RATE_MS);
  };

  const stopPolling = () => {
    if (!pollingInterval) return;
    clearInterval(pollingInterval);
    pollingInterval = null;
  };

  return { subscribe, setEmergencyStop, startPolling, stopPolling, fetchSystemStatus };
};

export const systemStore = createSystemStore();
