// src/stores/beverageStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { displayAdminPutJson } from '../lib/displayAdminApi.js';
import { logError, normalizeError } from '../lib/errorUtils.js';
import { sessionStore } from './sessionStore.js';

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

      update((state) => ({ ...state, loading: true, error: null }));
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
      if (!token) {
        throw new Error('Требуется повторный вход в систему');
      }

      update((state) => ({ ...state, loading: true, error: null }));
      try {
        const newBeverage = await invoke('create_beverage', { token, beverageData });
        update((state) => ({
          ...state,
          beverages: [...state.beverages, newBeverage].sort((left, right) => left.name.localeCompare(right.name)),
          loading: false,
          error: null,
        }));
        return newBeverage;
      } catch (error) {
        const errorMessage = toErrorMessage('beverageStore.createBeverage', error);
        update((state) => ({ ...state, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    updateBeverage: async (beverageId, beverageData) => {
      const token = get(sessionStore).token;
      if (!token) {
        throw new Error('Требуется повторный вход в систему');
      }

      update((state) => ({ ...state, loading: true, error: null }));
      try {
        const updatedBeverage = await displayAdminPutJson(`/api/beverages/${beverageId}`, beverageData);
        update((state) => ({
          ...state,
          beverages: state.beverages
            .map((item) => (item.beverage_id === beverageId ? updatedBeverage : item))
            .sort((left, right) => left.name.localeCompare(right.name)),
          loading: false,
          error: null,
        }));
        return updatedBeverage;
      } catch (error) {
        const errorMessage = toErrorMessage('beverageStore.updateBeverage', error);
        update((state) => ({ ...state, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },
  };
}

export const beverageStore = createBeverageStore();
