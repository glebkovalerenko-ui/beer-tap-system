import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils.js';
import { notifyForbiddenIfNeeded } from '../lib/forbidden.js';

const POLL_INTERVAL_MS = 10000;

const DEFAULT_MUTATION_CAPABILITIES = Object.freeze({
  claim: { enabled: false, reason: 'Endpoint временно отключён.' },
  escalate: { enabled: false, reason: 'Endpoint временно отключён.' },
  close: { enabled: false, reason: 'Endpoint временно отключён.' },
  note: { enabled: false, reason: 'Endpoint временно отключён.' },
});

const ACTION_TO_CAPABILITY_KEY = Object.freeze({
  claim_incident: 'claim',
  add_incident_note: 'note',
  escalate_incident: 'escalate',
  close_incident: 'close',
});

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function createIncidentStore() {
  const defaultReadOnlyReason = 'Incident mutation endpoints недоступны.';
  const initialState = {
    items: [],
    loading: false,
    isLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 10000,
    error: null,
    actionLoading: false,
    actionError: null,
    capabilities: { ...DEFAULT_MUTATION_CAPABILITIES },
    readOnly: true,
    readOnlyReason: defaultReadOnlyReason,
  };
  const { subscribe, set, update } = writable(initialState);
  const store = { subscribe };
  let timer = null;
  let incidentsInFlight = null;

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

  function resolveCapabilities(serverCapabilities = null) {
    const capabilities = { ...DEFAULT_MUTATION_CAPABILITIES };
    for (const key of Object.keys(capabilities)) {
      const candidate = serverCapabilities?.[key];
      const enabled = typeof candidate?.allowed === 'boolean'
        ? candidate.allowed
        : (typeof candidate?.enabled === 'boolean' ? candidate.enabled : null);
      if (candidate && typeof enabled === 'boolean') {
        capabilities[key] = {
          enabled,
          reason: enabled ? null : (candidate.disabled_reason || candidate.reason || defaultReadOnlyReason),
        };
      }
    }
    const readOnly = !Object.values(capabilities).some((capability) => capability?.enabled);
    const readOnlyReason = readOnly
      ? Object.values(capabilities).find((capability) => capability?.reason)?.reason || defaultReadOnlyReason
      : null;
    return { capabilities, readOnly, readOnlyReason };
  }

  async function fetchIncidents({ force = false, staleTtlMs = null } = {}) {
    const token = get(sessionStore).token;
    if (!token) return;
    const state = get(store);
    const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
    const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
    if (!force && hasFreshData) {
      return state.items;
    }
    if (incidentsInFlight) {
      return incidentsInFlight;
    }

    update((nextState) => ({ ...nextState, loading: nextState.items.length === 0, isLoading: true, error: null, actionError: null }));
    try {
      incidentsInFlight = invoke('get_incidents', { token, limit: 100 });
      const response = await incidentsInFlight;
      const items = Array.isArray(response) ? response : (response?.items || []);
      const capabilityState = resolveCapabilities(Array.isArray(response) ? null : response?.mutation_capabilities);
      update((state) => ({
        ...state,
        items,
        loading: false,
        isLoading: false,
        lastFetchedAt: Date.now(),
        error: null,
        ...capabilityState,
      }));
      return items;
    } catch (error) {
      update((state) => ({ ...state, loading: false, isLoading: false, error: toErrorMessage('incidentStore.fetchIncidents', error) }));
    } finally {
      incidentsInFlight = null;
    }
  }

  async function submitAction(command, incidentId, payload, context) {
    const token = withAuth();
    const capabilityKey = ACTION_TO_CAPABILITY_KEY[command];
    const capability = capabilityKey ? get(store).capabilities?.[capabilityKey] : null;
    if (capability && capability.enabled === false) {
      throw new Error(capability.reason || defaultReadOnlyReason);
    }
    update((state) => ({ ...state, actionLoading: true, actionError: null }));
    try {
      const item = await invoke(command, { token, incidentId, payload });
      mergeIncident(item);
      fetchIncidents({ force: true }).catch(() => {});
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
