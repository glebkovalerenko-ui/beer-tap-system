// src/stores/beverageStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

/**
 * @typedef {import('../../../src-tauri/src/api_client').Beverage} Beverage
 * @typedef {import('../../../src-tauri/src/api_client').BeveragePayload} BeveragePayload
 */

function createBeverageStore() {
  /** @type {import('svelte/store').Writable<{beverages: Beverage[], loading: boolean, error: string | null}>} */
  const { subscribe, set, update } = writable({
    beverages: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    /**
     * Запрашивает список всех напитков с бэкенда.
     */
    fetchBeverages: async () => {
      const token = get(sessionStore).token;
      if (!token) return;
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        /** @type {Beverage[]} */
        const beverages = await invoke('get_beverages', { token });
        set({ beverages, loading: false, error: null });
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        set({ beverages: [], loading: false, error: errorMessage });
      }
    },

    /**
     * Создает новый напиток.
     * @param {BeveragePayload} beverageData
     */
    createBeverage: async (beverageData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const newBeverage = await invoke('create_beverage', { token, beverageData });
        update(s => ({
          ...s,
          // Паттерн "Оптимистичное обновление": добавляем новый элемент и сортируем
          beverages: [...s.beverages, newBeverage].sort((a, b) => a.name.localeCompare(b.name)),
          loading: false,
        }));
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        update(s => ({ ...s, loading: false, error: errorMessage }));
        throw error; // Пробрасываем ошибку дальше, чтобы UI мог ее поймать
      }
    },
  };
}

export const beverageStore = createBeverageStore();