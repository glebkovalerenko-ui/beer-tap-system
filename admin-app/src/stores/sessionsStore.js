// @ts-nocheck
import { get, writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { logError, normalizeError } from '../lib/errorUtils.js';
import { notifyForbiddenIfNeeded } from '../lib/forbidden.js';
import { sessionStore } from './sessionStore.js';

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

function createSessionsStore() {
  const initialState = {
    generatedAt: null,
    filters: null,
    header: null,
    pinnedActiveSessions: [],
    items: [],
    detail: null,
    loading: false,
    isLoading: false,
    detailLoading: false,
    actionLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 15000,
    error: null,
    actionError: null,
  };

  const { subscribe, set, update } = writable(initialState);
  const store = { subscribe };
  let journalInFlight = null;
  let detailInFlight = null;

  function applyJournalResponse(response) {
    update((state) => ({
      ...state,
      generatedAt: response?.generated_at || null,
      filters: response?.applied_filters || null,
      header: response?.header || null,
      pinnedActiveSessions: response?.pinned_active_sessions || [],
      items: response?.items || [],
      loading: false,
      isLoading: false,
      lastFetchedAt: Date.now(),
      error: null,
    }));
  }

  async function fetchJournal(filters = {}, { force = false, staleTtlMs = null } = {}) {
    const token = ensureToken();
    const state = get(store);
    const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
    const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
    if (!force && hasFreshData && (state.items.length > 0 || state.pinnedActiveSessions.length > 0)) {
      return {
        generated_at: state.generatedAt,
        applied_filters: state.filters,
        header: state.header,
        pinned_active_sessions: state.pinnedActiveSessions,
        items: state.items,
      };
    }
    if (journalInFlight) {
      return journalInFlight;
    }

    update((current) => ({ ...current, loading: true, isLoading: true, error: null }));
    try {
      journalInFlight = invoke('get_operator_sessions', {
        token,
        periodPreset: filters.periodPreset || 'today',
        dateFrom: filters.dateFrom || null,
        dateTo: filters.dateTo || null,
        tapId: filters.tapId ? Number(filters.tapId) : null,
        status: filters.status || null,
        cardUid: filters.cardUid || null,
        completionSource: filters.completionSource || null,
        incidentOnly: Boolean(filters.incidentOnly),
        unsyncedOnly: Boolean(filters.unsyncedOnly),
        zeroVolumeAbortOnly: Boolean(filters.zeroVolumeAbortOnly),
        activeOnly: Boolean(filters.activeOnly),
      });
      const response = await journalInFlight;
      applyJournalResponse(response);
      return response;
    } catch (error) {
      const message = toErrorMessage('sessionsStore.fetchJournal', error);
      update((current) => ({ ...current, loading: false, isLoading: false, error: message }));
      throw new Error(message);
    } finally {
      journalInFlight = null;
    }
  }

  async function fetchDetail(visitId) {
    const token = ensureToken();
    if (detailInFlight && get(store).detail?.summary?.visit_id === visitId) {
      return detailInFlight;
    }
    update((state) => ({ ...state, detailLoading: true, error: null }));
    try {
      detailInFlight = invoke('get_operator_session_detail', { token, visitId });
      const detail = await detailInFlight;
      update((state) => ({ ...state, detail, detailLoading: false, error: null }));
      return detail;
    } catch (error) {
      const message = toErrorMessage('sessionsStore.fetchDetail', error);
      update((state) => ({ ...state, detailLoading: false, error: message }));
      throw new Error(message);
    } finally {
      detailInFlight = null;
    }
  }

  async function refreshAfterMutation(visitId, filters = null) {
    const currentFilters = filters || get(store).filters || {};
    await Promise.allSettled([
      fetchJournal(
        {
          periodPreset: currentFilters.period_preset || currentFilters.periodPreset || 'today',
          dateFrom: currentFilters.date_from || currentFilters.dateFrom || null,
          dateTo: currentFilters.date_to || currentFilters.dateTo || null,
          tapId: currentFilters.tap_id || currentFilters.tapId || null,
          status: currentFilters.status || null,
          cardUid: currentFilters.card_uid || currentFilters.cardUid || null,
          completionSource: currentFilters.completion_source || currentFilters.completionSource || null,
          incidentOnly: Boolean(currentFilters.incident_only ?? currentFilters.incidentOnly),
          unsyncedOnly: Boolean(currentFilters.unsynced_only ?? currentFilters.unsyncedOnly),
          zeroVolumeAbortOnly: Boolean(currentFilters.zero_volume_abort_only ?? currentFilters.zeroVolumeAbortOnly),
          activeOnly: Boolean(currentFilters.active_only ?? currentFilters.activeOnly),
        },
        { force: true }
      ),
      visitId ? fetchDetail(visitId) : Promise.resolve(),
    ]);
  }

  async function runMutation(context, callback, visitId) {
    update((state) => ({ ...state, actionLoading: true, actionError: null }));
    try {
      const result = await callback();
      await refreshAfterMutation(visitId);
      update((state) => ({ ...state, actionLoading: false, actionError: null }));
      return result;
    } catch (error) {
      notifyForbiddenIfNeeded(error);
      const message = toErrorMessage(context, error);
      update((state) => ({ ...state, actionLoading: false, actionError: message }));
      throw new Error(message);
    }
  }

  return {
    subscribe,
    fetchJournal,
    fetchDetail,
    clearDetail: () => update((state) => ({ ...state, detail: null, actionError: null })),
    clearActionError: () => update((state) => ({ ...state, actionError: null })),
    closeSession: ({ visitId, closedReason = 'operator_close', cardReturned = true }) => runMutation(
      'sessionsStore.closeSession',
      () => invoke('close_visit', { token: ensureToken(), visitId, closedReason, cardReturned }),
      visitId,
    ),
    forceUnlockSession: ({ visitId, reason, comment = null }) => runMutation(
      'sessionsStore.forceUnlockSession',
      () => invoke('force_unlock_visit', { token: ensureToken(), visitId, reason, comment }),
      visitId,
    ),
    reconcileSession: ({ visitId, tapId, shortId, volumeMl, amount, reason, comment = null }) => runMutation(
      'sessionsStore.reconcileSession',
      () => invoke('reconcile_pour', { token: ensureToken(), visitId, tapId, shortId, volumeMl, amount, reason, comment }),
      visitId,
    ),
    markLostCard: ({ visitId, reason = null, comment = null }) => runMutation(
      'sessionsStore.markLostCard',
      () => invoke('report_lost_card_from_visit', { token: ensureToken(), visitId, reason, comment }),
      visitId,
    ),
    reset: () => set(initialState),
  };
}

export const sessionsStore = createSessionsStore();

sessionStore.subscribe((session) => {
  if (!session.token) {
    sessionsStore.reset();
  }
});
