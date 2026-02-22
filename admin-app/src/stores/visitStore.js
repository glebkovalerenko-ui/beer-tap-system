import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

function createVisitStore() {
  const { subscribe, set, update } = writable({
    currentVisit: null,
    loading: false,
    error: null,
    notFound: false,
  });

  const withAuth = () => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Not authenticated');
    return token;
  };

  return {
    subscribe,

    clearCurrentVisit: () => {
      update((s) => ({ ...s, currentVisit: null, error: null, notFound: false }));
    },

    searchActiveVisit: async (query) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, notFound: false }));
      try {
        const visit = await invoke('search_active_visit', { token, query });
        set({ currentVisit: visit, loading: false, error: null, notFound: false });
        return visit;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        if (message.toLowerCase().includes('active visit not found') || message.includes('404')) {
          set({ currentVisit: null, loading: false, error: null, notFound: true });
          return null;
        }
        set({ currentVisit: null, loading: false, error: message, notFound: false });
        throw error;
      }
    },



    openVisit: async ({ guestId, cardUid = undefined }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null, notFound: false }));
      try {
        const payload = cardUid ? { token, guestId, cardUid } : { token, guestId };
        const visit = await invoke('open_visit', payload);
        update((s) => ({ ...s, currentVisit: visit, loading: false }));
        return visit;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },

    forceUnlock: async ({ visitId, reason, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const updatedVisit = await invoke('force_unlock_visit', { token, visitId, reason, comment });
        update((s) => ({ ...s, currentVisit: updatedVisit, loading: false }));
        return updatedVisit;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },

    closeVisit: async ({ visitId, closedReason, cardReturned = true }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const closedVisit = await invoke('close_visit', { token, visitId, closedReason, cardReturned });
        update((s) => ({ ...s, currentVisit: closedVisit, loading: false }));
        return closedVisit;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },
  };
}

export const visitStore = createVisitStore();
