// @ts-nocheck
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { logError, normalizeError } from '../lib/errorUtils.js';
import { sessionStore } from './sessionStore.js';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createOperatorSearchStore() {
  const initialState = {
    query: '',
    totalResults: 0,
    groups: [],
    loading: false,
    error: null,
  };

  const { subscribe, set, update } = writable(initialState);
  let requestCounter = 0;

  async function search(query, { limit = 5 } = {}) {
    const token = get(sessionStore).token;
    const normalizedQuery = String(query || '').trim();
    if (!token || normalizedQuery.length < 2) {
      set({ ...initialState, query: normalizedQuery });
      return { query: normalizedQuery, total_results: 0, groups: [] };
    }

    const requestId = ++requestCounter;
    update((state) => ({ ...state, query: normalizedQuery, loading: true, error: null }));
    try {
      const response = await invoke('search_operator_workspace', { token, query: normalizedQuery, limit });
      if (requestId !== requestCounter) {
        return response;
      }
      set({
        query: response?.query || normalizedQuery,
        totalResults: response?.total_results || 0,
        groups: response?.groups || [],
        loading: false,
        error: null,
      });
      return response;
    } catch (error) {
      const message = toErrorMessage('operatorSearchStore.search', error);
      if (requestId === requestCounter) {
        update((state) => ({ ...state, loading: false, error: message }));
      }
      throw new Error(message);
    }
  }

  return {
    subscribe,
    search,
    clear: () => {
      requestCounter += 1;
      set(initialState);
    },
  };
}

export const operatorSearchStore = createOperatorSearchStore();
