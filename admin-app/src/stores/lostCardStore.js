import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

const initialState = {
  items: [],
  loading: false,
  error: null,
  filters: {
    uid: '',
    reportedFrom: '',
    reportedTo: '',
  },
};

function createLostCardStore() {
  const { subscribe, update } = writable(initialState);
  let snapshot = initialState;
  subscribe((value) => {
    snapshot = value;
  });

  const withAuth = () => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Not authenticated');
    return token;
  };

  const fetchLostCards = async (overrides = {}) => {
    const token = withAuth();
    update((s) => ({ ...s, loading: true, error: null }));
    try {
      const filters = { ...snapshot.filters, ...overrides };
      const items = await invoke('list_lost_cards', {
        token,
        uid: filters.uid?.trim() || null,
        reportedFrom: filters.reportedFrom?.trim() || null,
        reportedTo: filters.reportedTo?.trim() || null,
      });
      update((s) => ({ ...s, items, filters, loading: false }));
      return items;
    } catch (error) {
      const message = toErrorMessage('lostCardStore.fetchLostCards', error);
      update((s) => ({ ...s, loading: false, error: message }));
      throw new Error(message);
    }
  };

  return {
    subscribe,

    setFilters: (nextFilters) => {
      update((s) => ({ ...s, filters: { ...s.filters, ...nextFilters } }));
    },

    fetchLostCards,

    restoreLostCard: async (cardUid) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await invoke('restore_lost_card', { token, cardUid });
        await fetchLostCards();
        update((s) => ({ ...s, loading: false }));
        return result;
      } catch (error) {
        const message = toErrorMessage('lostCardStore.restoreLostCard', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },

    resolveCard: async (cardUid) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const result = await invoke('resolve_card', { token, cardUid });
        update((s) => ({ ...s, loading: false }));
        return result;
      } catch (error) {
        const message = toErrorMessage('lostCardStore.resolveCard', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },
  };
}

export const lostCardStore = createLostCardStore();
