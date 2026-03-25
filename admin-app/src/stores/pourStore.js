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

  const initialState = {
    pours: [],
    feedItems: [],
    flowSummary: null,
    todaySummary: null,
    todaySummaryError: null,
    overview: null,
    loading: false,
    error: null,
  };
  const { subscribe, set, update } = writable(initialState);

  async function fetchPours() {
    const token = get(sessionStore).token;
    if (!token) {
      console.warn('Опрос наливов не запущен: отсутствует токен авторизации.');
      return;
    }

    update((s) => {
      if (s.pours.length === 0 && s.feedItems.length === 0) {
        return { ...s, loading: true, error: null };
      }
      return s;
    });

    try {
      const [overview, pours] = await Promise.all([
        invoke('get_operator_today', { token }),
        invoke('get_pours', { token, limit: 20 }),
      ]);
      set({
        pours,
        feedItems: overview?.feed_items || [],
        flowSummary: overview?.flow_summary || null,
        todaySummary: overview?.today_summary || null,
        todaySummaryError: null,
        overview: overview || null,
        loading: false,
        error: null,
      });
    } catch (error) {
      const errorMessage = toErrorMessage('pourStore.fetchPours', error);
      update((s) => ({ ...s, loading: false, error: errorMessage }));
      stopPolling();
    }
  }

  function startPolling() {
    if (pollInterval) return;
    console.log('Запуск опроса наливов.');
    fetchPours();
    pollInterval = setInterval(fetchPours, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollInterval) {
      console.log('Остановка опроса наливов.');
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  sessionStore.subscribe((session) => {
    if (session.token) {
      startPolling();
    } else {
      stopPolling();
      set(initialState);
    }
  });

  return {
    subscribe,
  };
}

export const pourStore = createPourStore();
