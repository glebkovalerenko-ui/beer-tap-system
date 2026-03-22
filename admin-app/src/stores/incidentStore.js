import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils.js';

const POLL_INTERVAL_MS = 10000;

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createIncidentStore() {
  const initialState = { items: [], loading: false, error: null };
  const { subscribe, set, update } = writable(initialState);
  let timer = null;

  async function fetchIncidents() {
    const token = get(sessionStore).token;
    if (!token) return;
    update((state) => ({ ...state, loading: state.items.length === 0, error: null }));
    try {
      const items = await invoke('get_incidents', { token, limit: 100 });
      set({ items, loading: false, error: null });
    } catch (error) {
      update((state) => ({ ...state, loading: false, error: toErrorMessage('incidentStore.fetchIncidents', error) }));
    }
  }

  function startPolling() {
    if (timer) return;
    fetchIncidents();
    timer = setInterval(fetchIncidents, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  }

  sessionStore.subscribe((session) => {
    if (session.token) startPolling();
    else {
      stopPolling();
      set(initialState);
    }
  });

  return { subscribe, fetchIncidents, startPolling, stopPolling };
}

export const incidentStore = createIncidentStore();
