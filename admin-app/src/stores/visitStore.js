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
    sessionHistory: [],
    sessionHistoryDetail: null,
    historyLoading: false,
    loading: false,
    isLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 15000,
    error: null,
  });
  let activeVisitsInFlight = null;

  const withAuth = () => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    return token;
  };

  return {
    subscribe,

    clearCurrentVisit: () => {
      update((s) => ({ ...s, currentVisit: null, error: null }));
    },

    clearSessionHistoryDetail: () => {
      update((s) => ({ ...s, sessionHistoryDetail: null }));
    },

    fetchActiveVisits: async ({ force = false, staleTtlMs = null } = {}) => {
      const token = withAuth();
      const state = get({ subscribe });
      const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
      const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
      if (!force && hasFreshData && state.activeVisits.length > 0) {
        return state.activeVisits;
      }
      if (activeVisitsInFlight) {
        return activeVisitsInFlight;
      }

      update((s) => ({ ...s, loading: true, isLoading: true, error: null }));
      try {
        activeVisitsInFlight = invoke('get_active_visits', { token });
        const activeVisits = await activeVisitsInFlight;
        update((s) => ({ ...s, activeVisits, loading: false, isLoading: false, lastFetchedAt: Date.now() }));
        return activeVisits;
      } catch (error) {
        const message = toErrorMessage('visitStore.fetchActiveVisits', error);
        update((s) => ({ ...s, loading: false, isLoading: false, error: message }));
        throw new Error(message);
      } finally {
        activeVisitsInFlight = null;
      }
    },

    fetchSessionHistory: async (filters = {}) => {
      const token = withAuth();
      update((s) => ({ ...s, historyLoading: true, error: null }));
      try {
        const sessionHistory = await invoke('get_session_history', {
          token,
          dateFrom: filters.dateFrom || null,
          dateTo: filters.dateTo || null,
          tapId: filters.tapId ? Number(filters.tapId) : null,
          status: filters.status || null,
          cardUid: filters.cardUid || null,
          incidentOnly: Boolean(filters.incidentOnly),
          unsyncedOnly: Boolean(filters.unsyncedOnly),
        });
        update((s) => ({ ...s, sessionHistory, historyLoading: false }));
        return sessionHistory;
      } catch (error) {
        const message = toErrorMessage('visitStore.fetchSessionHistory', error);
        update((s) => ({ ...s, historyLoading: false, error: message }));
        throw new Error(message);
      }
    },

    fetchSessionHistoryDetail: async (visitId) => {
      const token = withAuth();
      update((s) => ({ ...s, historyLoading: true, error: null }));
      try {
        const sessionHistoryDetail = await invoke('get_session_history_detail', { token, visitId });
        update((s) => ({ ...s, sessionHistoryDetail, historyLoading: false }));
        return sessionHistoryDetail;
      } catch (error) {
        const message = toErrorMessage('visitStore.fetchSessionHistoryDetail', error);
        update((s) => ({ ...s, historyLoading: false, error: message }));
        throw new Error(message);
      }
    },

    setCurrentVisit: (visit) => {
      update((s) => ({ ...s, currentVisit: visit }));
    },

    openVisit: async ({ guestId, cardUid }) => {
      const token = withAuth();
      if (!cardUid?.trim()) throw new Error('Для открытия визита требуется карта.');
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const visit = await invoke('open_visit', { token, guestId, cardUid: cardUid.trim() });
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

    closeVisit: async ({ visitId, closedReason, returnedCardUid }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        if (!returnedCardUid?.trim()) throw new Error('Для обычного закрытия нужно отсканировать возвращённую карту.');
        const closedVisit = await invoke('close_visit', {
          token,
          visitId,
          closedReason,
          returnedCardUid: returnedCardUid.trim(),
        });
        update((s) => ({ ...s, currentVisit: closedVisit, loading: false }));
        return closedVisit;
      } catch (error) {
        const message = toErrorMessage('visitStore.closeVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },

    serviceCloseVisit: async ({ visitId, closedReason, reasonCode, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const closedVisit = await invoke('service_close_visit', { token, visitId, closedReason, reasonCode, comment });
        update((s) => ({ ...s, currentVisit: closedVisit, loading: false }));
        return closedVisit;
      } catch (error) {
        const message = toErrorMessage('visitStore.serviceCloseVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },

    reissueCard: async ({ visitId, cardUid, reason, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const visit = await invoke('reissue_card_for_visit', { token, visitId, cardUid, reason, comment });
        update((s) => ({ ...s, currentVisit: visit, loading: false }));
        return visit;
      } catch (error) {
        const message = toErrorMessage('visitStore.reissueCard', error);
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

    restoreLostCardForVisit: async ({ visitId, reason = null, comment = null }) => {
      const token = withAuth();
      update((s) => ({ ...s, loading: true, error: null }));
      try {
        const visit = await invoke('restore_lost_card_for_visit', { token, visitId, reason, comment });
        update((s) => ({ ...s, currentVisit: visit, loading: false }));
        return visit;
      } catch (error) {
        const message = toErrorMessage('visitStore.restoreLostCardForVisit', error);
        update((s) => ({ ...s, loading: false, error: message }));
        throw new Error(message);
      }
    },
  };
}

export const visitStore = createVisitStore();
