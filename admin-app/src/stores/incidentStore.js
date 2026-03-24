import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils.js';
import { notifyForbiddenIfNeeded } from '../lib/forbidden.js';

const POLL_INTERVAL_MS = 10000;

const MUTATION_CAPABILITIES = Object.freeze({
  claim: true,
  escalate: true,
  close: true,
  note: true,
});

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
    capabilities: { ...MUTATION_CAPABILITIES },
    readOnly: !Object.values(MUTATION_CAPABILITIES).some(Boolean),
    readOnlyReason: !Object.values(MUTATION_CAPABILITIES).some(Boolean) ? 'Incident mutation endpoints недоступны.' : null,
  };
  const { subscribe, set, update } = writable(initialState);
  let timer = null;

  function withAuth() {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    return token;
  }

  function mergeIncident(updatedItem) {
    if (!updatedItem?.incident_id) return;
    update((state) => ({
      ...state,
      items: state.items.some((item) => item.incident_id === updatedItem.incident_id)
        ? state.items.map((item) => item.incident_id === updatedItem.incident_id ? updatedItem : item)
        : [updatedItem, ...state.items],
      actionLoading: false,
      actionError: null,
    }));
  }

  async function fetchIncidents() {
    const token = get(sessionStore).token;
    if (!token) return;
    update((state) => ({ ...state, loading: state.items.length === 0, error: null, actionError: null }));
    try {
      const items = await invoke('get_incidents', { token, limit: 100 });
      update((state) => ({
        ...state,
        items,
        loading: false,
        error: null,
        capabilities: { ...MUTATION_CAPABILITIES },
        readOnly: !Object.values(MUTATION_CAPABILITIES).some(Boolean),
        readOnlyReason: !Object.values(MUTATION_CAPABILITIES).some(Boolean) ? 'Incident mutation endpoints недоступны.' : null,
      }));
    } catch (error) {
      update((state) => ({ ...state, loading: false, error: toErrorMessage('incidentStore.fetchIncidents', error) }));
    }
  }

  async function submitAction(command, incidentId, payload, context) {
    const token = withAuth();
    update((state) => ({ ...state, actionLoading: true, actionError: null }));
    try {
      const item = await invoke(command, { token, incidentId, payload });
      mergeIncident(item);
      return item;
    } catch (error) {
      notifyForbiddenIfNeeded(error);
      const message = toErrorMessage(context, error);
      update((state) => ({ ...state, actionLoading: false, actionError: message }));
      throw new Error(message);
    }
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
    claimIncident: ({ incidentId, owner, note }) => submitAction('claim_incident', incidentId, { owner, note }, 'incidentStore.claimIncident'),
    escalateIncident: ({ incidentId, reason, note }) => submitAction('escalate_incident', incidentId, { reason, note }, 'incidentStore.escalateIncident'),
    closeIncident: ({ incidentId, resolutionSummary, note }) => submitAction('close_incident', incidentId, { resolution_summary: resolutionSummary, note }, 'incidentStore.closeIncident'),
    addIncidentNote: ({ incidentId, note }) => submitAction('add_incident_note', incidentId, { note }, 'incidentStore.addIncidentNote'),
  };
}

export const incidentStore = createIncidentStore();
