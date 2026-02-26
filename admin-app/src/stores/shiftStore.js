import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeErrorMessage } from '../lib/errorUtils';

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
    if (!token) throw new Error('Не выполнен вход в систему');
    return token;
  };

  const mapError = (context, error) => {
    logError(context, error);
    return normalizeErrorMessage(error);
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
        const message = mapError('shiftStore.fetchCurrent', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = mapError('shiftStore.openShift', error);
        if (message.includes('Shift already open')) {
          const current = await invoke('get_current_shift', { token });
          const normalized = normalizeCurrent(current);
          update((s) => ({ ...s, ...normalized, loading: false }));
          return normalized.shift;
        }
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },

    closeShift: async () => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, closeErrorReason: null }));
      try {
        const shift = await invoke('close_shift', { token });
        update((s) => ({ ...s, isOpen: false, shift, loading: false, closeErrorReason: null }));
        return shift;
      } catch (error) {
        const message = mapError('shiftStore.closeShift', error);
        const reason = closeReasonFromError(message);
        update((s) => ({ ...s, loading: false, error: message, closeErrorReason: reason }));
        throw new Error(reason || message);
      }
    },

    fetchXReport: async (shiftId) => {
      const token = withAuth();
      try {
        return await invoke('get_shift_x_report', { token, shiftId });
      } catch (error) {
        throw new Error(mapError('shiftStore.fetchXReport', error));
      }
    },

    createZReport: async (shiftId) => {
      const token = withAuth();
      try {
        return await invoke('create_shift_z_report', { token, shiftId });
      } catch (error) {
        throw new Error(mapError('shiftStore.createZReport', error));
      }
    },

    fetchZReport: async (shiftId) => {
      const token = withAuth();
      try {
        return await invoke('get_shift_z_report', { token, shiftId });
      } catch (error) {
        throw new Error(mapError('shiftStore.fetchZReport', error));
      }
    },

    listZReports: async (fromDate, toDate) => {
      const token = withAuth();
      try {
        return await invoke('list_shift_z_reports', { token, fromDate, toDate });
      } catch (error) {
        throw new Error(mapError('shiftStore.listZReports', error));
      }
    },

    recordTopUp: () => {},
  };
}

export const shiftStore = createShiftStore();
