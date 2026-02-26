// src/stores/kegStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

/**
 * @typedef {import('../../../src-tauri/src/api_client').Keg} Keg
 * @typedef {import('../../../src-tauri/src/api_client').KegPayload} KegPayload
 * @typedef {import('../../../src-tauri/src/api_client').KegUpdatePayload} KegUpdatePayload
 */

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createKegStore() {
  /** @type {import('svelte/store').Writable<{kegs: Keg[], loading: boolean, error: string | null}>} */
  const { subscribe, set, update } = writable({
    kegs: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    fetchKegs: async () => {
      const token = get(sessionStore).token;
      if (!token) return;

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        /** @type {Keg[]} */
        const kegs = await invoke('get_kegs', { token });
        set({ kegs, loading: false, error: null });
      } catch (error) {
        const errorMessage = toErrorMessage('kegStore.fetchKegs', error);
        set({ kegs: [], loading: false, error: errorMessage });
      }
    },

    createKeg: async (kegData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const newKeg = await invoke('create_keg', { token, kegData });
        update((s) => ({
          ...s,
          kegs: [...s.kegs, newKeg].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
          loading: false,
        }));
      } catch (error) {
        const errorMessage = toErrorMessage('kegStore.createKeg', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    updateKeg: async (kegId, kegData) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const updatedKeg = await invoke('update_keg', { token, kegId, kegData });
        update((s) => {
          const updatedKegs = s.kegs.map((k) => (k.keg_id === kegId ? updatedKeg : k));
          return { ...s, kegs: updatedKegs, loading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('kegStore.updateKeg', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    deleteKeg: async (kegId) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        await invoke('delete_keg', { token, kegId });
        update((s) => {
          const updatedKegs = s.kegs.filter((k) => k.keg_id !== kegId);
          return { ...s, kegs: updatedKegs, loading: false };
        });
      } catch (error) {
        const errorMessage = toErrorMessage('kegStore.deleteKeg', error);
        update((s) => ({ ...s, loading: false, error: errorMessage }));
        throw new Error(errorMessage);
      }
    },

    markKegAsUsed: (kegId) => {
      update((s) => {
        const updatedKegs = s.kegs.map((k) => (k.keg_id === kegId ? { ...k, status: 'in_use' } : k));
        return { ...s, kegs: updatedKegs };
      });
    },

    markKegAsAvailable: (kegId) => {
      update((s) => {
        const updatedKegs = s.kegs.map((k) => (k.keg_id === kegId ? { ...k, status: 'full' } : k));
        return { ...s, kegs: updatedKegs };
      });
    },
  };
}

export const kegStore = createKegStore();
