// src/stores/tapStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { displayAdminGetJson, displayAdminPutJson } from '../lib/displayAdminApi.js';
import { logError, normalizeError } from '../lib/errorUtils.js';
import { sessionStore } from './sessionStore.js';

/** @typedef {import('../../../src-tauri/src/api_client').Tap} Tap */

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function ensureToken() {
  const token = get(sessionStore).token;
  if (!token) {
    throw new Error('Требуется повторный вход в систему');
  }

  return token;
}

function createTapStore() {
  /** @type {import('svelte/store').Writable<{taps: Tap[], loading: boolean, error: string | null}>} */
  const { subscribe, set, update } = writable({
    taps: [],
    loading: false,
    error: null,
  });

  return {
    subscribe,

    fetchTaps: async () => {
      const token = get(sessionStore).token;
      if (!token) return;

      update((state) => ({ ...state, loading: true, error: null }));
      try {
        const taps = await invoke('get_taps', { token });
        set({ taps, loading: false, error: null });
      } catch (error) {
        const errorMessage = toErrorMessage('tapStore.fetchTaps', error);
        set({ taps: [], loading: false, error: errorMessage });
      }
    },

    assignKegToTap: async (tapId, kegId) => {
      const token = ensureToken();

      try {
        /** @type {Tap} */
        const updatedTap = await invoke('assign_keg_to_tap', { token, tapId, kegId });

        update((state) => ({
          ...state,
          taps: state.taps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));

        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.assignKegToTap', error));
      }
    },

    unassignKegFromTap: async (tapId) => {
      const token = ensureToken();

      try {
        const updatedTap = await invoke('unassign_keg_from_tap', { token, tapId });
        update((state) => ({
          ...state,
          taps: state.taps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.unassignKegFromTap', error));
      }
    },

    updateTapStatus: async (tapId, status) => {
      const token = ensureToken();

      try {
        const payload = { status };
        const updatedTap = await invoke('update_tap', { token, tapId, payload });
        update((state) => ({
          ...state,
          taps: state.taps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.updateTapStatus', error));
      }
    },

    fetchTapDisplayConfig: async (tapId) => {
      ensureToken();

      try {
        return await displayAdminGetJson(`/api/taps/${tapId}/display-config`);
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.fetchTapDisplayConfig', error));
      }
    },

    updateTapDisplayConfig: async (tapId, payload) => {
      ensureToken();

      try {
        return await displayAdminPutJson(`/api/taps/${tapId}/display-config`, payload);
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.updateTapDisplayConfig', error));
      }
    },
  };
}

export const tapStore = createTapStore();
