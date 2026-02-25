import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';

function createVisitStore() {
  const { subscribe, update } = writable({
    activeVisits: [],
    currentVisit: null,
    loading: false,
    error: null,
  });

  const withAuth = () => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Not authenticated');
    return token;
  };

  return {
    subscribe,

    clearCurrentVisit: () => {
      update((s) => ({ ...s, currentVisit: null, error: null }));
    },

    fetchActiveVisits: async () => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const activeVisits = await invoke('get_active_visits', { token });
        update((s) => ({ ...s, activeVisits, loading: false }));
        return activeVisits;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },

    setCurrentVisit: (visit) => {
      update((s) => ({ ...s, currentVisit: visit }));
    },

    openVisit: async ({ guestId, cardUid = undefined }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
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

    assignCardToVisit: async ({ visitId, cardUid }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const visit = await invoke('assign_card_to_visit', { token, visitId, cardUid });
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

    reconcilePour: async ({ visitId, tapId, shortId, volumeMl, amount, reason, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const visit = await invoke('reconcile_pour', {
          token,
          visitId,
          tapId,
          shortId,
          volumeMl,
          amount,
          reason,
          comment,
        });
        update((s) => ({ ...s, currentVisit: visit, loading: false }));
        return visit;
      } catch (error) {
        const message = error?.message || error?.toString?.() || 'Unknown error';
        update((s) => ({ ...s, loading: false, error: message }));
        throw error;
      }
    },
  };
}

export const visitStore = createVisitStore();
