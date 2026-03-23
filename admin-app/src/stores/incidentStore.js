import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils.js';

const POLL_INTERVAL_MS = 10000;

const ACTION_CAPABILITIES = Object.freeze({
  claim: false,
  escalate: false,
  close: false,
  note: false,
});

const READ_ONLY_REASON = 'Backend incident API currently exposes only listing. Claim/escalation/closure/note actions are shown as operator workflow requirements until durable endpoints are implemented.';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createIncidentStore() {
  const initialState = {
    items: [],
    loading: false,
    error: null,
    actionLoading: false,
    actionError: null,
    capabilities: ACTION_CAPABILITIES,
    readOnly: true,
    readOnlyReason: READ_ONLY_REASON,
  };
  const { subscribe, set, update } = writable(initialState);
  let timer = null;

  function withAuth() {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    return token;
  }

  async function fetchIncidents() {
    const token = get(sessionStore).token;
    if (!token) return;
    update((state) => ({ ...state, loading: state.items.length === 0, error: null, actionError: null }));
    try {
      const items = await invoke('get_incidents', { token, limit: 100 });
      update((state) => ({ ...state, items, loading: false, error: null, capabilities: ACTION_CAPABILITIES, readOnly: true, readOnlyReason: READ_ONLY_REASON }));
    } catch (error) {
      update((state) => ({ ...state, loading: false, error: toErrorMessage('incidentStore.fetchIncidents', error) }));
    }
  }

  async function runUnsupportedAction(actionLabel) {
    withAuth();
    const message = `${actionLabel} пока недоступно: backend incident API работает в read-only режиме.`;
    update((state) => ({ ...state, actionLoading: false, actionError: message }));
    throw new Error(message);
  }

  function clearActionError() {
    update((state) => ({ ...state, actionError: null }));
  }

  function startPolling() {
    if (timer) return;
    fetchIncidents();
    timer = setInterval(fetchIncidents, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  }

  sessionStore.subscribe((session) => {
    if (session.token) startPolling();
    else {
      stopPolling();
      set(initialState);
    }
  });

  return {
    subscribe,
    fetchIncidents,
    startPolling,
    stopPolling,
    clearActionError,
    claimIncident: () => runUnsupportedAction('Взятие инцидента в работу'),
    escalateIncident: () => runUnsupportedAction('Эскалация инцидента'),
    closeIncident: () => runUnsupportedAction('Закрытие инцидента'),
    addIncidentNote: () => runUnsupportedAction('Добавление заметки к инциденту'),
  };
}

export const incidentStore = createIncidentStore();
