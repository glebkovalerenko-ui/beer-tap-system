// src/stores/tapStore.js
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

/** @typedef {import('../../../src-tauri/src/api_client').Tap} Tap */

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
      
      update(s => ({ ...s, loading: true, error: null }));
      try {
        const taps = await invoke('get_taps', { token });
        set({ taps, loading: false, error: null });
      } catch (error) {
        const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
        set({ taps: [], loading: false, error: errorMessage });
      }
    },

    /**
     * Назначает кегу на кран и обновляет состояние.
     * @param {number} tapId
     * @param {string} kegId
     * @returns {Promise<Tap>} Обновленный объект крана
     */
    assignKegToTap: async (tapId, kegId) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");

      // Не устанавливаем глобальный loading, чтобы не блокировать весь UI
      try {
        /** @type {Tap} */
        const updatedTap = await invoke('assign_keg_to_tap', { token, tapId, kegId });
        
        // Паттерн "Оптимистичное обновление"
        update(s => {
          const updatedTaps = s.taps.map(t => t.tap_id === tapId ? updatedTap : t);
          return { ...s, taps: updatedTaps };
        });

        return updatedTap; // Возвращаем для возможной доп. обработки в UI
      } catch (error) {
        // Ошибку пробрасываем выше, чтобы модальное окно могло ее отобразить
        throw error;
      }
    },
    
    unassignKegFromTap: async (tapId) => {
      const token = get(sessionStore).token;
      if (!token) throw new Error("Not authenticated");
      
      const updatedTap = await invoke('unassign_keg_from_tap', { token, tapId });
      update(s => {
        const updatedTaps = s.taps.map(t => t.tap_id === tapId ? updatedTap : t);
        return { ...s, taps: updatedTaps };
      });
      return updatedTap;
    },

    updateTapStatus: async (tapId, status) => {
        const token = get(sessionStore).token;
        if (!token) throw new Error("Not authenticated");

        const payload = { status };
        const updatedTap = await invoke('update_tap', { token, tapId, payload });
        update(s => {
            const updatedTaps = s.taps.map(t => t.tap_id === tapId ? updatedTap : t);
            return { ...s, taps: updatedTaps };
        });
        return updatedTap;
    },

  };
}

export const tapStore = createTapStore();