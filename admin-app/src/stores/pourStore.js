// src/stores/pourStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

const POLL_INTERVAL_MS = 10000;

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

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
      console.warn('fetchPours called without a token. Polling will not start.');
      return;
    }

    update((s) => {
      if (s.pours.length === 0) {
        return { ...s, loading: true, error: null };
      }
      return s;
    });

    try {
      const pours = await invoke('get_pours', { token, limit: 20 });
      set({ pours, loading: false, error: null });
    } catch (error) {
      const errorMessage = toErrorMessage('pourStore.fetchPours', error);
      update((s) => ({ ...s, loading: false, error: errorMessage }));
      stopPolling();
    }
  }

  function startPolling() {
    if (pollInterval) return;
    console.log('Starting pours polling...');
    fetchPours();
    pollInterval = setInterval(fetchPours, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollInterval) {
      console.log('Stopping pours polling.');
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  sessionStore.subscribe((session) => {
    if (session.token) {
      startPolling();
    } else {
      stopPolling();
      set({ pours: [], loading: false, error: null });
    }
  });

  return {
    subscribe,
  };
}

export const pourStore = createPourStore();
