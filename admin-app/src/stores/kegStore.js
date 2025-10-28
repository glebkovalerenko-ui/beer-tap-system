// src/stores/kegStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

/**
 * @typedef {import('../../../src-tauri/src/api_client').Keg} Keg
 * @typedef {import('../../../src-tauri/src/api_client').KegPayload} KegPayload
 * @typedef {import('../../../src-tauri/src/api_client').KegUpdatePayload} KegUpdatePayload
 */

function createKegStore() {
  /** @type {import('svelte/store').Writable<{kegs: Keg[], loading: boolean, error: string | null}>} */
  const { subscribe, set, update } = writable({
    kegs: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    /**
     * Запрашивает список всех кег с бэкенда.
     */
    fetchKegs: async () => {
      const token = get(sessionStore).token;
      if (!token) return;
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        /** @type {Keg[]} */
        const kegs = await invoke('get_kegs', { token });
        set({ kegs, loading: false, error: null });
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        set({ kegs: [], loading: false, error: errorMessage });
      }
    },

    /**
     * Создает новую кегу.
     * @param {KegPayload} kegData
     */
    createKeg: async (kegData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const newKeg = await invoke('create_keg', { token, kegData });
        update(s => ({
          ...s,
          kegs: [...s.kegs, newKeg].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
          loading: false,
        }));
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        update(s => ({ ...s, loading: false, error: errorMessage }));
        throw error;
      }
    },

    /**
     * Обновляет данные кеги.
     * @param {string} kegId
     * @param {KegUpdatePayload} kegData
     */
    updateKeg: async (kegId, kegData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      update(s => ({ ...s, loading: true, error: null }));
      try {
        const updatedKeg = await invoke('update_keg', { token, kegId, kegData });
        update(s => {
          const updatedKegs = s.kegs.map(k => k.keg_id === kegId ? updatedKeg : k);
          return { ...s, kegs: updatedKegs, loading: false };
        });
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        update(s => ({ ...s, loading: false, error: errorMessage }));
        throw error;
      }
    },

    /**
     * Удаляет кегу.
     * @param {string} kegId
     */
    deleteKeg: async (kegId) => {
        const token = get(sessionStore).token;
        if (!token) throw new Error("Not authenticated");
  
        update(s => ({ ...s, loading: true, error: null }));
        try {
          await invoke('delete_keg', { token, kegId });
          update(s => {
            const updatedKegs = s.kegs.filter(k => k.keg_id !== kegId);
            return { ...s, kegs: updatedKegs, loading: false };
          });
        } catch (error) {
          const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
          update(s => ({ ...s, loading: false, error: errorMessage }));
          throw error;
        }
      },
      
      /**
       * Локально обновляет статус кеги на 'in_use'.
       * Вызывается после успешного назначения кеги на кран,
       * чтобы UI был консистентным без перезагрузки.
       * @param {string} kegId
       */
      markKegAsUsed: (kegId) => {
        update(s => {
          const updatedKegs = s.kegs.map(k => {
            if (k.keg_id === kegId) {
              return { ...k, status: 'in_use' };
            }
            return k;
          });
          return { ...s, kegs: updatedKegs };
        });
      },

      markKegAsAvailable: (kegId) => {
      update(s => {
        const updatedKegs = s.kegs.map(k => {
          if (k.keg_id === kegId) {
            // Бэкенд возвращает статус 'full', если кега не пуста
            return { ...k, status: 'full' };
          }
          return k;
          });
          return { ...s, kegs: updatedKegs };
        });
      },
  };
}

export const kegStore = createKegStore();