import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

const INITIAL_STATE = {
  isOpen: false,
  shift: null,
  loading: false,
  error: null,
  closeErrorReason: null,
};

function closeReasonFromError(message) {
  const text = (message || '').toString();
  if (text.includes('active_visits_exist')) return 'Есть активные визиты';
  if (text.includes('pending_sync_pours_exist')) return 'Есть несинхронизированные наливы';
  return null;
}

function normalizeCurrent(payload) {
  const shift = payload?.shift || null;
  const isOpen = payload?.status === 'open' && !!shift;
  return { isOpen, shift };
}

function createShiftStore() {
  const { subscribe, set, update } = writable(INITIAL_STATE);

  const withAuth = () => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Not authenticated');
    return token;
  };

  return {
    subscribe,

    reset: () => set({ ...INITIAL_STATE }),

    fetchCurrent: async () => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, closeErrorReason: null }));
      try {
        const current = await invoke('get_current_shift', { token });
        const normalized = normalizeCurrent(current);
        update((s) => ({ ...s, ...normalized, loading: false }));
        return normalized;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },

    openShift: async () => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, closeErrorReason: null }));
      try {
        const shift = await invoke('open_shift', { token });
        update((s) => ({ ...s, isOpen: true, shift, loading: false }));
        return shift;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        if (message.includes('Shift already open')) {
          const current = await invoke('get_current_shift', { token });
          const normalized = normalizeCurrent(current);
          update((s) => ({ ...s, ...normalized, loading: false }));
          return normalized.shift;
        }
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },

    closeShift: async () => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, closeErrorReason: null }));
      try {
        const shift = await invoke('close_shift', { token });
        update((s) => ({ ...s, isOpen: false, shift: null, loading: false, closeErrorReason: null }));
        return shift;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        const reason = closeReasonFromError(message);
        update((s) => ({ ...s, loading: false, error: message, closeErrorReason: reason }));
        throw new Error(reason || message);
      }
    },

    recordTopUp: () => {},
  };
}

export const shiftStore = createShiftStore();
