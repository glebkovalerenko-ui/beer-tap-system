// src/stores/tapStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

/** @typedef {import('../../../src-tauri/src/api_client').Tap} Tap */

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
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

      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const taps = await invoke('get_taps', { token });
        set({ taps, loading: false, error: null });
      } catch (error) {
        const errorMessage = toErrorMessage('tapStore.fetchTaps', error);
        set({ taps: [], loading: false, error: errorMessage });
      }
    },

    assignKegToTap: async (tapId, kegId) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      try {
        /** @type {Tap} */
        const updatedTap = await invoke('assign_keg_to_tap', { token, tapId, kegId });

        update((s) => {
          const updatedTaps = s.taps.map((t) => (t.tap_id === tapId ? updatedTap : t));
          return { ...s, taps: updatedTaps };
        });

        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.assignKegToTap', error));
      }
    },

    unassignKegFromTap: async (tapId) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      try {
        const updatedTap = await invoke('unassign_keg_from_tap', { token, tapId });
        update((s) => {
          const updatedTaps = s.taps.map((t) => (t.tap_id === tapId ? updatedTap : t));
          return { ...s, taps: updatedTaps };
        });
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.unassignKegFromTap', error));
      }
    },

    updateTapStatus: async (tapId, status) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error('Not authenticated');

      try {
        const payload = { status };
        const updatedTap = await invoke('update_tap', { token, tapId, payload });
        update((s) => {
          const updatedTaps = s.taps.map((t) => (t.tap_id === tapId ? updatedTap : t));
          return { ...s, taps: updatedTaps };
        });
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.updateTapStatus', error));
      }
    },
  };
}

export const tapStore = createTapStore();
