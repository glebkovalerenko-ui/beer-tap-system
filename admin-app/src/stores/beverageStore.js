// src/stores/beverageStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

/**
 * @typedef {import('../../../src-tauri/src/api_client').Beverage} Beverage
 * @typedef {import('../../../src-tauri/src/api_client').BeveragePayload} BeveragePayload
 */

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createBeverageStore() {
  /** @type {import('svelte/store').Writable<{beverages: Beverage[], loading: boolean, error: string | null}>} */
  const { subscribe, set, update } = writable({
    beverages: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    fetchBeverages: async () => {
      const token = get(sessionStore).token;
      if (!token) return;

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        /** @type {Beverage[]} */
        const beverages = await invoke('get_beverages', { token });
        set({ beverages, loading: false, error: null });
      } catch (error) {
        const errorMessage = toErrorMessage('beverageStore.fetchBeverages', error);
        set({ beverages: [], loading: false, error: errorMessage });
      }
    },

    createBeverage: async (beverageData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const newBeverage = await invoke('create_beverage', { token, beverageData });
        update((s) => ({
          ...s,
          beverages: [...s.beverages, newBeverage].sort((a, b) => a.name.localeCompare(b.name)),
          loading: false,
        }));
      } catch (error) {
        const errorMessage = toErrorMessage('beverageStore.createBeverage', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },
  };
}

export const beverageStore = createBeverageStore();
