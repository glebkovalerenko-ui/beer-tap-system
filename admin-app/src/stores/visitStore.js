import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore';
import { logError, normalizeError } from '../lib/errorUtils';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

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
        const message = toErrorMessage('visitStore.fetchActiveVisits', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = toErrorMessage('visitStore.openVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = toErrorMessage('visitStore.assignCardToVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = toErrorMessage('visitStore.forceUnlock', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = toErrorMessage('visitStore.closeVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
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
        const message = toErrorMessage('visitStore.reconcilePour', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },

    reportLostCard: async ({ visitId, reason = null, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const response = await invoke('report_lost_card_from_visit', { token, visitId, reason, comment });
        update((s) => ({ ...s, currentVisit: response.visit, loading: false }));
        return response;
      } catch (error) {
        const message = toErrorMessage('visitStore.reportLostCard', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },
  };
}

export const visitStore = createVisitStore();
