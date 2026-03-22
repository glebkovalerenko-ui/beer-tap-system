import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';

import { displayAdminGetJson, displayAdminPutJson } from '../lib/displayAdminApi.js';
import { logError, normalizeError } from '../lib/errorUtils.js';
import { sessionStore } from './sessionStore.js';

/** @typedef {import('../../../src-tauri/src/api_client').Tap} Tap */

const PRODUCT_STATE_LABELS = {
  ready: 'Готов к продаже',
  pouring: 'Идёт налив',
  needs_help: 'Требует внимания',
  unavailable: 'Недоступен',
  syncing: 'Синхронизация',
  no_keg: 'Нет кеги',
};

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

function toNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value.replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function toDate(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function minutesSince(value) {
  const date = toDate(value);
  if (!date) return null;
  return Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
}

function labelFromState(state) {
  return PRODUCT_STATE_LABELS[state] || state || 'Нет данных';
}

function titleCase(text) {
  if (!text) return '';
  return String(text).charAt(0).toUpperCase() + String(text).slice(1);
}

function humanizeCode(code) {
  if (!code) return null;
  return titleCase(String(code).replaceAll('_', ' '));
}

function deriveProductState(rawTap, activeSession, recentEvents) {
  const tap = rawTap || {};
  if (!tap.keg_id) return 'no_keg';
  if (tap.product_state) return tap.product_state;
  if (tap.sync_state === 'syncing' || tap.status === 'processing_sync') return 'syncing';
  if (activeSession || recentEvents.some((item) => item.reason === 'authorized_pour_in_progress' || item.event_status === 'started')) return 'pouring';
  if (tap.status === 'active') return 'ready';
  if (tap.status === 'cleaning' || tap.status === 'empty' || tap.status === 'locked') return 'unavailable';
  if (recentEvents.some((item) => item.reason && item.reason !== 'authorized_pour_in_progress')) return 'needs_help';
  return 'needs_help';
}

function buildSubsystemStatus(rawValue, fallbackState, fallbackLabel) {
  if (rawValue && typeof rawValue === 'object') {
    return {
      state: rawValue.state || rawValue.status || fallbackState,
      label: rawValue.label || rawValue.detail || fallbackLabel,
      detail: rawValue.detail || rawValue.message || null,
    };
  }

  return {
    state: rawValue || fallbackState,
    label: fallbackLabel,
    detail: null,
  };
}

function buildSessionAction(activeSession) {
  const visitId = activeSession?.visit_id || null;
  return visitId
    ? {
        label: `Сессия #${visitId}`,
        href: '#/sessions',
        visitId,
      }
    : null;
}

function buildIncidentAction(item) {
  const incidentId = item?.incident_id || item?.related_incident_id || item?.incident?.incident_id || null;
  return incidentId
    ? {
        label: `Инцидент #${incidentId}`,
        href: '#/incidents',
        incidentId,
      }
    : null;
}

function eventPriority(item) {
  const priority = item?.priority || item?.severity || item?.incident?.priority || null;
  if (priority) return priority;
  if (item?.item_type === 'pour') return item?.status === 'rejected' ? 'high' : 'medium';
  if (item?.reason === 'flow_detected_when_valve_closed_without_active_session') return 'critical';
  if (item?.event_status === 'started') return 'medium';
  return 'low';
}

function eventTone(priority) {
  if (priority === 'critical') return 'critical';
  if (priority === 'high') return 'warning';
  if (priority === 'medium') return 'info';
  return 'neutral';
}

function describeOperatorEvent(item, activeSession) {
  if (item?.item_type === 'pour') {
    return {
      title: item.status === 'rejected' ? 'Продажа отклонена' : 'Продажа завершена',
      description: item.status === 'rejected'
        ? 'Налив не был подтверждён как продажа.'
        : 'Завершён платный налив по активной сессии.',
    };
  }

  if (item?.reason === 'authorized_pour_in_progress' || item?.session_state === 'authorized_session') {
    return {
      title: item?.event_status === 'stopped' ? 'Налив по сессии остановлен' : 'Идёт налив по активной сессии',
      description: 'Контроллер фиксирует пролив в рамках авторизованной сессии.',
    };
  }

  if (item?.reason === 'flow_detected_when_valve_closed_without_active_session') {
    return {
      title: 'Пролив без активной сессии',
      description: 'Поток зафиксирован при закрытом клапане или без открытой сессии.',
    };
  }

  if (item?.event_status === 'stopped') {
    return {
      title: 'Поток остановлен',
      description: 'Контроллер сообщил об остановке пролива.',
    };
  }

  if (item?.event_status === 'started') {
    return {
      title: 'Поток зафиксирован',
      description: activeSession ? 'Есть признаки нового пролива по текущей сессии.' : 'Контроллер сообщил о начале потока.',
    };
  }

  return {
    title: humanizeCode(item?.item_type) || 'Событие крана',
    description: humanizeCode(item?.reason || item?.event_status || item?.status) || 'Событие поступило без расшифровки кода.',
  };
}

function buildOperatorHistory(recentEvents, activeSession) {
  return recentEvents.map((item, index) => {
    const summary = describeOperatorEvent(item, activeSession);
    const priority = eventPriority(item);
    const visitId = item?.visit_id || item?.session_id || activeSession?.visit_id || null;

    return {
      id: item?.item_id || `${item?.item_type || 'event'}-${item?.timestamp || item?.ended_at || item?.created_at || index}`,
      title: summary.title,
      description: summary.description,
      priority,
      tone: eventTone(priority),
      priorityLabel: humanizeCode(priority) || 'Low',
      happenedAt: item?.ended_at || item?.timestamp || item?.created_at || item?.started_at || null,
      volumeMl: toNumber(item?.volume_ml),
      amount: item?.amount_charged ?? null,
      rawStatus: item?.status || item?.event_status || item?.reason || null,
      sessionAction: visitId
        ? {
            label: `Сессия #${visitId}`,
            href: '#/sessions',
            visitId,
          }
        : null,
      incidentAction: buildIncidentAction(item),
    };
  });
}


function deriveTapAttentionItems(tapView) {
  const items = [];
  const tapLabel = tapView.display_name || tapView.name || `Кран #${tapView.tap_id}`;

  if (tapView.operations.heartbeat.isStale) {
    items.push({
      key: `stale-heartbeat-${tapView.tap_id}`,
      kind: 'stale_heartbeat',
      severity: 'warning',
      title: tapLabel,
      description: `Нет heartbeat ${tapView.operations.heartbeat.minutesAgo} мин`,
      actionLabel: 'Открыть кран',
      href: '#/taps',
    });
  }

  if (!tapView.keg_id) {
    items.push({
      key: `no-keg-${tapView.tap_id}`,
      kind: 'no_keg',
      severity: 'warning',
      title: tapLabel,
      description: 'Кран без назначенной кеги.',
      actionLabel: 'Открыть кран',
      href: '#/taps',
    });
  }

  if (tapView.operations.syncState.code === 'syncing') {
    items.push({
      key: `unsynced-flow-${tapView.tap_id}`,
      kind: 'unsynced_flow',
      severity: 'warning',
      title: tapLabel,
      description: 'Есть локальный пролив, ожидающий синхронизацию.',
      actionLabel: 'Открыть сессию',
      href: '#/sessions',
      visitId: tapView.active_session?.visit_id || null,
    });
  }

  if (['warning', 'critical', 'error', 'offline'].includes(tapView.operations.readerStatus.state)) {
    items.push({
      key: `reader-offline-${tapView.tap_id}`,
      kind: 'reader_offline',
      severity: tapView.operations.readerStatus.state === 'critical' || tapView.operations.readerStatus.state === 'error' ? 'critical' : 'warning',
      title: tapLabel,
      description: tapView.operations.readerStatus.detail || tapView.operations.readerStatus.label,
      actionLabel: 'Открыть кран',
      href: '#/taps',
    });
  }

  if (['warning', 'critical', 'error', 'offline'].includes(tapView.operations.displayStatus.state)) {
    items.push({
      key: `display-offline-${tapView.tap_id}`,
      kind: 'display_offline',
      severity: tapView.operations.displayStatus.state === 'critical' || tapView.operations.displayStatus.state === 'error' ? 'critical' : 'warning',
      title: tapLabel,
      description: tapView.operations.displayStatus.detail || tapView.operations.displayStatus.label,
      actionLabel: 'Открыть кран',
      href: '#/taps',
    });
  }

  if (['warning', 'critical', 'error', 'offline'].includes(tapView.operations.controllerStatus.state)) {
    items.push({
      key: `controller-offline-${tapView.tap_id}`,
      kind: 'controller_offline',
      severity: tapView.operations.controllerStatus.state === 'critical' || tapView.operations.controllerStatus.state === 'error' ? 'critical' : 'warning',
      title: tapLabel,
      description: tapView.operations.controllerStatus.detail || tapView.operations.controllerStatus.label,
      actionLabel: 'Открыть кран',
      href: '#/taps',
    });
  }

  return items;
}

function deriveTapSummary(taps) {
  const attentionItems = taps.flatMap((tap) => tap.operations.attentionItems || []);
  return {
    activeCount: taps.filter((tap) => tap.status === 'active').length,
    pouringCount: taps.filter((tap) => tap.operations.productState === 'pouring').length,
    noKegCount: attentionItems.filter((item) => item.kind === 'no_keg').length,
    staleHeartbeatCount: attentionItems.filter((item) => item.kind === 'stale_heartbeat').length,
    unsyncedFlowCount: attentionItems.filter((item) => item.kind === 'unsynced_flow').length,
    readerOfflineCount: attentionItems.filter((item) => item.kind === 'reader_offline').length,
    displayOfflineCount: attentionItems.filter((item) => item.kind === 'display_offline').length,
    controllerOfflineCount: attentionItems.filter((item) => item.kind === 'controller_offline').length,
    attentionItems,
  };
}

function buildTapView(rawTap, context = {}) {
  const activeVisits = context.activeVisits || [];
  const feedItems = context.feedItems || [];

  const activeSession = rawTap.active_session
    || activeVisits.find((visit) => visit.active_tap_id === rawTap.tap_id)
    || null;

  const recentEvents = Array.isArray(rawTap.recent_events) && rawTap.recent_events.length > 0
    ? rawTap.recent_events
    : feedItems
        .filter((item) => item.tap_id === rawTap.tap_id)
        .slice(0, 5);

  const keg = rawTap.keg || null;
  const initialVolume = toNumber(keg?.initial_volume_ml);
  const currentVolume = toNumber(keg?.current_volume_ml);
  const remainingPercent = initialVolume > 0 ? Math.max(0, Math.round((currentVolume / initialVolume) * 100)) : 0;

  const heartbeatAt = rawTap.last_heartbeat_at || rawTap.updated_at || activeSession?.lock_set_at || null;
  const heartbeatMinutes = minutesSince(heartbeatAt);
  const productState = deriveProductState(rawTap, activeSession, recentEvents);
  const syncState = rawTap.sync_state || (rawTap.status === 'processing_sync' ? 'syncing' : activeSession ? 'live' : 'idle');
  const currentPourVolumeMl = toNumber(rawTap.current_pour_volume_ml ?? recentEvents[0]?.volume_ml);
  const currentPourAmount = rawTap.current_pour_amount ?? recentEvents[0]?.amount_charged ?? null;
  const sessionAction = buildSessionAction(activeSession);

  const tapView = {
    ...rawTap,
    keg,
    active_session: activeSession,
    operations: {
      productState,
      productStateLabel: labelFromState(productState),
      beverageName: keg?.beverage?.name || rawTap.beverage_name || 'Напиток не назначен',
      beverageStyle: keg?.beverage?.style || rawTap.beverage_style || null,
      remainingVolumeMl: currentVolume,
      initialVolumeMl: initialVolume,
      remainingPercent,
      controllerStatus: buildSubsystemStatus(rawTap.controller_status, productState === 'needs_help' ? 'warning' : 'ok', rawTap.controller_status_label || 'Контроллер отвечает'),
      displayStatus: buildSubsystemStatus(rawTap.display_status, rawTap.display_enabled === false ? 'warning' : 'ok', rawTap.display_status_label || (rawTap.display_enabled === false ? 'Экран выключен' : 'Экран на связи')),
      readerStatus: buildSubsystemStatus(rawTap.reader_status, activeSession ? 'busy' : 'ok', rawTap.reader_status_label || (activeSession?.card_uid ? `Карта ${activeSession.card_uid}` : 'Ридер готов')),
      activeSessionSummary: activeSession
        ? {
            guestName: activeSession.guest_full_name || [activeSession.guest?.first_name, activeSession.guest?.last_name].filter(Boolean).join(' ') || 'Гость без имени',
            cardUid: activeSession.card_uid || null,
            visitId: activeSession.visit_id || null,
            openedAt: activeSession.opened_at || null,
            lockedAt: activeSession.lock_set_at || null,
            balance: activeSession.balance || activeSession.guest?.balance || null,
            sessionAction,
          }
        : null,
      heartbeat: {
        at: heartbeatAt,
        minutesAgo: heartbeatMinutes,
        isStale: heartbeatMinutes != null ? heartbeatMinutes >= 5 : false,
      },
      syncState: {
        code: syncState,
        label: syncState === 'syncing' ? 'Ожидает синхронизацию с backend' : syncState === 'live' ? 'Локальная сессия активна' : 'Синхронизирован',
      },
      currentPour: {
        volumeMl: currentPourVolumeMl,
        amount: currentPourAmount,
        isActive: Boolean(activeSession || (recentEvents[0] && recentEvents[0].event_status !== 'stopped')),
      },
      recentEvents,
      operatorHistory: buildOperatorHistory(recentEvents, activeSession),
      liveStatus: rawTap.live_status || (productState === 'pouring' ? 'Идёт налив' : productState === 'ready' ? 'Готов к продаже' : 'Нужна проверка'),
    },
  };

  tapView.operations.attentionItems = deriveTapAttentionItems(tapView);
  return tapView;
}

function createTapStore() {
  const initialState = {
    rawTaps: [],
    taps: [],
    summary: deriveTapSummary([]),
    loading: false,
    error: null,
    context: {
      activeVisits: [],
      feedItems: [],
    },
  };

  const { subscribe, set, update } = writable(initialState);
  let currentState = initialState;
  subscribe((state) => {
    currentState = state;
  });

  function commit(state) {
    currentState = state;
    set(state);
  }

  function refreshDerived(state) {
    const taps = state.rawTaps.map((tap) => buildTapView(tap, state.context));
    return {
      ...state,
      taps,
      summary: deriveTapSummary(taps),
    };
  }

  return {
    subscribe,

    fetchTaps: async () => {
      const token = get(sessionStore).token;
      if (!token) return;

      update((state) => ({ ...state, loading: true, error: null }));
      try {
        const taps = await invoke('get_taps', { token });
        commit(refreshDerived({ ...currentState, rawTaps: taps, loading: false, error: null }));
      } catch (error) {
        const errorMessage = toErrorMessage('tapStore.fetchTaps', error);
        commit({ ...currentState, rawTaps: [], taps: [], loading: false, error: errorMessage });
      }
    },

    setOperationalContext: ({ activeVisits = [], feedItems = [] } = {}) => {
      update((state) => refreshDerived({
        ...state,
        context: {
          activeVisits,
          feedItems,
        },
      }));
    },

    assignKegToTap: async (tapId, kegId) => {
      const token = ensureToken();

      try {
        const updatedTap = await invoke('assign_keg_to_tap', { token, tapId, kegId });

        update((state) => refreshDerived({
          ...state,
          rawTaps: state.rawTaps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));

        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.assignKegToTap', error));
      }
    },

    unassignKegFromTap: async (tapId) => {
      const token = ensureToken();

      try {
        const updatedTap = await invoke('unassign_keg_from_tap', { token, tapId });
        update((state) => refreshDerived({
          ...state,
          rawTaps: state.rawTaps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.unassignKegFromTap', error));
      }
    },

    updateTapStatus: async (tapId, status) => {
      const token = ensureToken();

      try {
        const payload = { status };
        const updatedTap = await invoke('update_tap', { token, tapId, payload });
        update((state) => refreshDerived({
          ...state,
          rawTaps: state.rawTaps.map((tap) => (tap.tap_id === tapId ? updatedTap : tap)),
        }));
        return updatedTap;
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.updateTapStatus', error));
      }
    },

    fetchTapDisplayConfig: async (tapId) => {
      ensureToken();

      try {
        return await displayAdminGetJson(`/api/taps/${tapId}/display-config`);
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.fetchTapDisplayConfig', error));
      }
    },

    updateTapDisplayConfig: async (tapId, payload) => {
      ensureToken();

      try {
        return await displayAdminPutJson(`/api/taps/${tapId}/display-config`, payload);
      } catch (error) {
        throw new Error(toErrorMessage('tapStore.updateTapDisplayConfig', error));
      }
    },
  };
}

export const tapStore = createTapStore();
