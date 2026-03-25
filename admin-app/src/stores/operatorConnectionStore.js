// @ts-nocheck
import { get, writable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { getApiBaseUrl, initializeBackendBaseUrl } from '../lib/config.js';
import { ensureCardsGuestsData, ensureIncidentsData, ensureOperatorShellData } from './operatorShellOrchestrator.js';
import { guestStore } from './guestStore.js';
import { incidentStore } from './incidentStore.js';
import { pourStore } from './pourStore.js';
import { sessionStore } from './sessionStore.js';
import { sessionsStore } from './sessionsStore.js';
import { systemStore } from './systemStore.js';
import { tapStore } from './tapStore.js';
import { visitStore } from './visitStore.js';

const SHORT_POLL_INTERVAL_MS = 1000;
const REDUCED_POLL_INTERVAL_MS = 4000;
const HEARTBEAT_TIMEOUT_MS = 10000;
const REDUCED_MODE_AFTER_MS = 45000;
const RECONNECT_BACKOFF_MS = [1000, 2000, 5000, 10000, 20000, 60000, 120000];

function toWebSocketUrl(baseUrl, websocketPath, ticket) {
  const parsed = new URL(baseUrl);
  parsed.protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
  parsed.pathname = websocketPath;
  parsed.search = `ticket=${encodeURIComponent(ticket)}`;
  return parsed.toString();
}

function now() {
  return Date.now();
}

function normalizeRoute(route) {
  const path = String(route || window?.location?.hash?.replace(/^#/, '') || '/today');
  if (!path || path === '/') return '/today';
  if (path.startsWith('/sessions')) return '/sessions';
  if (path.startsWith('/taps')) return '/taps';
  if (path.startsWith('/cards-guests')) return '/cards-guests';
  if (path.startsWith('/incidents')) return '/incidents';
  if (path.startsWith('/system')) return '/system';
  return path;
}

function extractSessionFilters(rawFilters) {
  if (!rawFilters) {
    return { periodPreset: 'today' };
  }
  return {
    periodPreset: rawFilters.period_preset || rawFilters.periodPreset || 'today',
    dateFrom: rawFilters.date_from || rawFilters.dateFrom || '',
    dateTo: rawFilters.date_to || rawFilters.dateTo || '',
    tapId: rawFilters.tap_id || rawFilters.tapId || '',
    status: rawFilters.status || '',
    cardUid: rawFilters.card_uid || rawFilters.cardUid || '',
    completionSource: rawFilters.completion_source || rawFilters.completionSource || '',
    incidentOnly: Boolean(rawFilters.incident_only ?? rawFilters.incidentOnly),
    unsyncedOnly: Boolean(rawFilters.unsynced_only ?? rawFilters.unsyncedOnly),
    zeroVolumeAbortOnly: Boolean(rawFilters.zero_volume_abort_only ?? rawFilters.zeroVolumeAbortOnly),
    activeOnly: Boolean(rawFilters.active_only ?? rawFilters.activeOnly),
  };
}

async function refetchSessionsRoute() {
  const state = get(sessionsStore);
  const filters = extractSessionFilters(state.filters);
  await sessionsStore.fetchJournal(filters, { force: true }).catch(() => {});
  const selectedVisitId = state.detail?.summary?.visit_id;
  if (selectedVisitId) {
    await sessionsStore.fetchDetail(selectedVisitId).catch(() => {});
  }
}

async function refetchVisibleRoute(route) {
  switch (normalizeRoute(route)) {
    case '/today':
      await Promise.allSettled([
        pourStore.fetchOverview({ force: true }),
        tapStore.fetchTaps({ force: true }),
        visitStore.fetchActiveVisits({ force: true }),
        systemStore.fetchSystemStatus({ force: true }),
        ensureIncidentsData({ reason: 'realtime-invalidation', force: true }),
      ]);
      return;
    case '/taps':
      await Promise.allSettled([
        tapStore.fetchTaps({ force: true }),
        visitStore.fetchActiveVisits({ force: true }),
        systemStore.fetchSystemStatus({ force: true }),
      ]);
      return;
    case '/sessions':
      await refetchSessionsRoute();
      return;
    case '/cards-guests':
      await Promise.allSettled([
        ensureCardsGuestsData({ reason: 'realtime-invalidation', force: true }),
        guestStore.fetchGuests?.({ force: true }),
      ]);
      return;
    case '/incidents':
      await Promise.allSettled([
        ensureIncidentsData({ reason: 'realtime-invalidation', force: true }),
        incidentStore.fetchIncidents({ force: true }),
      ]);
      return;
    case '/system':
      await systemStore.fetchSystemStatus({ force: true }).catch(() => {});
      return;
    default:
      await ensureOperatorShellData({ reason: 'realtime-invalidation', force: true });
  }
}

function createOperatorConnectionStore() {
  const initialState = {
    started: false,
    connected: false,
    transport: 'websocket',
    mode: 'online',
    readOnly: false,
    reason: null,
    error: null,
    currentRoute: '/today',
    lastHeartbeatAt: null,
    lastMessageAt: null,
    lastSnapshotAt: null,
    reconnectAttempts: 0,
    degradedSince: null,
  };

  const { subscribe, update, set } = writable(initialState);
  const store = { subscribe };

  let socket = null;
  let socketClosedIntentionally = false;
  let heartbeatWatchdog = null;
  let pollingTimer = null;
  let reconnectTimer = null;
  let reducedModeTimer = null;
  let pendingRefreshTimer = null;

  function patchState(patch) {
    update((state) => ({ ...state, ...patch }));
  }

  function clearTimers() {
    if (heartbeatWatchdog) clearInterval(heartbeatWatchdog);
    if (pollingTimer) clearInterval(pollingTimer);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (reducedModeTimer) clearTimeout(reducedModeTimer);
    if (pendingRefreshTimer) clearTimeout(pendingRefreshTimer);
    heartbeatWatchdog = null;
    pollingTimer = null;
    reconnectTimer = null;
    reducedModeTimer = null;
    pendingRefreshTimer = null;
  }

  function setDegradedState(transport, reason) {
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    patchState((() => {
      const current = get(store);
      return {
        connected: false,
        transport,
        mode: offline ? 'offline' : 'backend_degraded',
        readOnly: true,
        reason,
        degradedSince: current.degradedSince || now(),
      };
    })());
  }

  function scheduleVisibleRouteRefresh(reason = 'realtime') {
    if (pendingRefreshTimer) {
      return;
    }
    pendingRefreshTimer = setTimeout(async () => {
      pendingRefreshTimer = null;
      await refetchVisibleRoute(get(store).currentRoute);
      patchState({ lastSnapshotAt: now(), error: null, reason: get(store).transport === 'websocket' ? null : reason });
    }, 200);
  }

  function startPolling(intervalMs, transport, reason) {
    if (pollingTimer) clearInterval(pollingTimer);
    setDegradedState(transport, reason);
    scheduleVisibleRouteRefresh(reason);
    pollingTimer = setInterval(() => {
      scheduleVisibleRouteRefresh(reason);
    }, intervalMs);
  }

  function scheduleReconnect() {
    if (reconnectTimer || !get(sessionStore).token) {
      return;
    }
    const attempts = Math.min(get(store).reconnectAttempts, RECONNECT_BACKOFF_MS.length - 1);
    const delay = RECONNECT_BACKOFF_MS[attempts];
    patchState({ reconnectAttempts: attempts + 1 });
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectWebSocket().catch(() => {});
    }, delay);
  }

  function enterShortPolling(reason) {
    startPolling(SHORT_POLL_INTERVAL_MS, 'short_polling', reason);
    if (reducedModeTimer) clearTimeout(reducedModeTimer);
    reducedModeTimer = setTimeout(() => {
      startPolling(REDUCED_POLL_INTERVAL_MS, 'reduced_polling', reason);
    }, REDUCED_MODE_AFTER_MS);
    scheduleReconnect();
  }

  function handleSocketFailure(reason) {
    if (socketClosedIntentionally) {
      return;
    }
    if (socket) {
      try {
        socket.close();
      } catch {}
      socket = null;
    }
    enterShortPolling(reason);
  }

  function beginHeartbeatWatchdog() {
    if (heartbeatWatchdog) clearInterval(heartbeatWatchdog);
    heartbeatWatchdog = setInterval(() => {
      const state = get(store);
      if (!state.connected || !state.lastHeartbeatAt) {
        return;
      }
      if (now() - state.lastHeartbeatAt > HEARTBEAT_TIMEOUT_MS) {
        handleSocketFailure('heartbeat_timeout');
      }
    }, 1000);
  }

  async function connectWebSocket() {
    const token = get(sessionStore).token;
    if (!token) {
      return;
    }

    await initializeBackendBaseUrl();
    const ticketResponse = await invoke('get_operator_stream_ticket', { token });
    const websocketUrl = toWebSocketUrl(
      getApiBaseUrl(),
      ticketResponse?.websocket_path || '/api/operator/stream',
      ticketResponse?.ticket,
    );

    socketClosedIntentionally = false;
    if (socket) {
      try {
        socket.close();
      } catch {}
    }

    socket = new WebSocket(websocketUrl);
    socket.addEventListener('open', () => {
      patchState({
        started: true,
        connected: true,
        transport: 'websocket',
        mode: 'online',
        readOnly: false,
        reason: null,
        error: null,
        reconnectAttempts: 0,
        degradedSince: null,
        lastHeartbeatAt: now(),
        lastMessageAt: now(),
      });
      if (pollingTimer) clearInterval(pollingTimer);
      pollingTimer = null;
      if (reducedModeTimer) clearTimeout(reducedModeTimer);
      reducedModeTimer = null;
      beginHeartbeatWatchdog();
      scheduleVisibleRouteRefresh('websocket_connected');
    });
    socket.addEventListener('message', (event) => {
      let payload = null;
      try {
        payload = JSON.parse(event.data);
      } catch {
        payload = null;
      }
      patchState({
        lastMessageAt: now(),
        lastHeartbeatAt: now(),
      });
      if (!payload?.event_type || payload.event_type === 'heartbeat' || payload.event_type === 'hello') {
        return;
      }
      scheduleVisibleRouteRefresh(payload.reason || payload.event_type);
    });
    socket.addEventListener('close', () => {
      handleSocketFailure('socket_closed');
    });
    socket.addEventListener('error', () => {
      handleSocketFailure('socket_error');
    });
  }

  function start() {
    if (!get(sessionStore).token) {
      return;
    }
    const currentState = get(store);
    if (currentState.started && (socket || pollingTimer || reconnectTimer)) {
      return;
    }
    patchState({ started: true, currentRoute: normalizeRoute(get(store).currentRoute) });
    connectWebSocket().catch((error) => {
      patchState({ error: error?.message || String(error || 'stream_connect_failed') });
      enterShortPolling('stream_connect_failed');
    });
  }

  function stop() {
    clearTimers();
    socketClosedIntentionally = true;
    if (socket) {
      try {
        socket.close();
      } catch {}
      socket = null;
    }
    set(initialState);
  }

  return {
    subscribe,
    start,
    stop,
    setActiveRoute(route) {
      const normalized = normalizeRoute(route);
      patchState({ currentRoute: normalized });
      if (get(store).started) {
        scheduleVisibleRouteRefresh('route_change');
      }
    },
    forceRefresh() {
      scheduleVisibleRouteRefresh('manual_refresh');
    },
  };
}

export const operatorConnectionStore = createOperatorConnectionStore();

sessionStore.subscribe((session) => {
  if (session.token) {
    operatorConnectionStore.start();
  } else {
    operatorConnectionStore.stop();
  }
});
