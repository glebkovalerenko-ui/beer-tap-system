// @ts-nocheck
import { get, writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { logError, normalizeError } from '../lib/errorUtils.js';
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

function createOperatorPoursStore() {
  const initialState = {
    generatedAt: null,
    filters: null,
    header: null,
    items: [],
    detail: null,
    loading: false,
    detailLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 15000,
    error: null,
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
      items: response?.items || [],
      loading: false,
      lastFetchedAt: Date.now(),
      error: null,
    }));
  }

  async function fetchJournal(filters = {}, { force = false, staleTtlMs = null } = {}) {
    const token = ensureToken();
    const state = get(store);
    const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
    const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
    if (!force && hasFreshData && state.items.length > 0) {
      return {
        generated_at: state.generatedAt,
        applied_filters: state.filters,
        header: state.header,
        items: state.items,
      };
    }
    if (journalInFlight) {
      return journalInFlight;
    }

    update((current) => ({ ...current, loading: true, error: null }));
    try {
      journalInFlight = invoke('get_operator_pours', {
        token,
        periodPreset: filters.periodPreset || 'today',
        dateFrom: filters.dateFrom || null,
        dateTo: filters.dateTo || null,
        tapId: filters.tapId ? Number(filters.tapId) : null,
        guestQuery: filters.guestQuery || null,
        visitId: filters.visitId || null,
        status: filters.status || null,
        problemOnly: Boolean(filters.problemOnly),
        nonSaleOnly: Boolean(filters.nonSaleOnly),
        zeroVolumeOnly: Boolean(filters.zeroVolumeOnly),
        timeoutOnly: Boolean(filters.timeoutOnly),
        deniedOnly: Boolean(filters.deniedOnly),
        saleMode: filters.saleMode || 'all',
      });
      const response = await journalInFlight;
      applyJournalResponse(response);
      return response;
    } catch (error) {
      const message = toErrorMessage('operatorPoursStore.fetchJournal', error);
      update((current) => ({ ...current, loading: false, error: message }));
      throw new Error(message);
    } finally {
      journalInFlight = null;
    }
  }

  async function fetchDetail(pourRef) {
    const token = ensureToken();
    if (detailInFlight && get(store).detail?.summary?.pour_ref === pourRef) {
      return detailInFlight;
    }

    update((state) => ({ ...state, detailLoading: true, error: null }));
    try {
      detailInFlight = invoke('get_operator_pour_detail', { token, pourRef });
      const detail = await detailInFlight;
      update((state) => ({ ...state, detail, detailLoading: false, error: null }));
      return detail;
    } catch (error) {
      const message = toErrorMessage('operatorPoursStore.fetchDetail', error);
      update((state) => ({ ...state, detailLoading: false, error: message }));
      throw new Error(message);
    } finally {
      detailInFlight = null;
    }
  }

  return {
    subscribe,
    fetchJournal,
    fetchDetail,
    clearDetail: () => update((state) => ({ ...state, detail: null })),
    reset: () => set(initialState),
  };
}

export const operatorPoursStore = createOperatorPoursStore();

sessionStore.subscribe((session) => {
  if (!session.token) {
    operatorPoursStore.reset();
  }
});
