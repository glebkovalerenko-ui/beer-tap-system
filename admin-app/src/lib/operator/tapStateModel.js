export const TAP_OPERATOR_STATES = Object.freeze({
  READY: 'ready',
  POURING: 'pouring',
  NEEDS_HELP: 'needs_help',
  UNAVAILABLE: 'unavailable',
  SYNCING: 'syncing',
  NO_KEG: 'no_keg',
});

export const TAP_OPERATOR_STATE_META = Object.freeze({
  [TAP_OPERATOR_STATES.READY]: {
    key: TAP_OPERATOR_STATES.READY,
    label: '\u0413\u043e\u0442\u043e\u0432',
    shortLabel: '\u0413\u043e\u0442\u043e\u0432',
    eyebrow: '\u041c\u043e\u0436\u043d\u043e \u043d\u0430\u043b\u0438\u0432\u0430\u0442\u044c',
    icon: '\u25cf',
    tone: 'ok',
    layout: 'steady',
    badgeStyle: 'pill',
    iconShape: 'dot',
    containerStyle: 'calm',
    headline: '\u041a\u0440\u0430\u043d \u0433\u043e\u0442\u043e\u0432 \u043a \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u043c\u0443 \u0433\u043e\u0441\u0442\u044e',
  },
  [TAP_OPERATOR_STATES.POURING]: {
    key: TAP_OPERATOR_STATES.POURING,
    label: '\u041b\u044c\u0451\u0442',
    shortLabel: '\u041b\u044c\u0451\u0442',
    eyebrow: '\u041d\u0430\u043b\u0438\u0432 \u0438\u0434\u0451\u0442 \u0441\u0435\u0439\u0447\u0430\u0441',
    icon: '\u23f5',
    tone: 'live',
    layout: 'live',
    badgeStyle: 'pill',
    iconShape: 'pulse',
    containerStyle: 'live',
    headline: '\u0421\u0435\u0439\u0447\u0430\u0441 \u0438\u0434\u0451\u0442 \u043d\u0430\u043b\u0438\u0432',
  },
  [TAP_OPERATOR_STATES.NEEDS_HELP]: {
    key: TAP_OPERATOR_STATES.NEEDS_HELP,
    label: '\u041d\u0443\u0436\u043d\u0430 \u043f\u043e\u043c\u043e\u0449\u044c',
    shortLabel: '\u041d\u0443\u0436\u043d\u0430 \u043f\u043e\u043c\u043e\u0449\u044c',
    eyebrow: '\u0422\u0440\u0435\u0431\u0443\u0435\u0442 \u0432\u043c\u0435\u0448\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430',
    icon: '!',
    tone: 'warn',
    layout: 'stacked',
    badgeStyle: 'callout',
    iconShape: 'alert',
    containerStyle: 'alert',
    headline: '\u041e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u0443 \u043d\u0443\u0436\u043d\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043a\u0440\u0430\u043d',
  },
  [TAP_OPERATOR_STATES.UNAVAILABLE]: {
    key: TAP_OPERATOR_STATES.UNAVAILABLE,
    label: '\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d',
    shortLabel: '\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d',
    eyebrow: '\u0421\u043d\u044f\u0442 \u0441 \u043f\u0440\u043e\u0434\u0430\u0436\u0438',
    icon: '\u00d7',
    tone: 'muted',
    layout: 'stacked',
    badgeStyle: 'slab',
    iconShape: 'block',
    containerStyle: 'blocked',
    headline: '\u041a\u0440\u0430\u043d \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u0432\u044b\u0432\u0435\u0434\u0435\u043d \u0438\u0437 \u043f\u0440\u043e\u0434\u0430\u0436\u0438',
  },
  [TAP_OPERATOR_STATES.SYNCING]: {
    key: TAP_OPERATOR_STATES.SYNCING,
    label: '\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f',
    shortLabel: '\u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044f',
    eyebrow: '\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 backend',
    icon: '\u21bb',
    tone: 'sync',
    layout: 'steady',
    badgeStyle: 'pill',
    iconShape: 'orbit',
    containerStyle: 'sync',
    headline: '\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 \u0435\u0449\u0451 \u043d\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u044b backend',
  },
  [TAP_OPERATOR_STATES.NO_KEG]: {
    key: TAP_OPERATOR_STATES.NO_KEG,
    label: '\u041d\u0435\u0442 \u043a\u0435\u0433\u0438',
    shortLabel: '\u041d\u0435\u0442 \u043a\u0435\u0433\u0438',
    eyebrow: '\u041d\u0443\u0436\u043d\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u043a\u0435\u0433\u0443',
    icon: '\u25cb',
    tone: 'empty',
    layout: 'empty',
    badgeStyle: 'outline',
    iconShape: 'ring',
    containerStyle: 'empty',
    headline: '\u041a\u0440\u0430\u043d \u043d\u0435 \u0441\u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u043e\u0434\u0430\u0432\u0430\u0442\u044c \u0431\u0435\u0437 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0451\u043d\u043d\u043e\u0439 \u043a\u0435\u0433\u0438',
  },
});

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

export function labelFromState(state) {
  return TAP_OPERATOR_STATE_META[state]?.label || state || '\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445';
}

export function humanizeCode(code) {
  if (!code) return null;
  const text = String(code).replaceAll('_', ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function reasonFromEvent(item) {
  if (!item) return null;
  if (item.reason === 'flow_detected_when_valve_closed_without_active_session') {
    return '\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 \u0443\u0432\u0438\u0434\u0435\u043b \u043f\u043e\u0442\u043e\u043a \u0431\u0435\u0437 \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0433\u043e \u0432\u0438\u0437\u0438\u0442\u0430 \u0438\u043b\u0438 \u043f\u0440\u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u043e\u043c \u043a\u043b\u0430\u043f\u0430\u043d\u0435.';
  }
  if (item.status === 'rejected' && item.item_type === 'pour') {
    return '\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u043d\u0430\u043b\u0438\u0432 \u0431\u044b\u043b \u043e\u0442\u043a\u043b\u043e\u043d\u0451\u043d \u0438 \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438.';
  }
  if (item.reason && item.reason !== 'authorized_pour_in_progress') {
    return humanizeCode(item.reason);
  }
  if (item.event_status === 'started') {
    return '\u041f\u043e\u0442\u043e\u043a \u043d\u0430\u0447\u0430\u043b\u0441\u044f, \u043d\u043e \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u0441\u043a\u0438\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u0435\u0449\u0451 \u043d\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d.';
  }
  return null;
}

export function eventPriority(item) {
  const priority = item?.priority || item?.severity || item?.incident?.priority || null;
  if (priority) return priority;
  if (item?.item_type === 'pour') return item?.status === 'rejected' ? 'high' : 'medium';
  if (item?.reason === 'flow_detected_when_valve_closed_without_active_session') return 'critical';
  if (item?.event_status === 'started') return 'medium';
  return 'low';
}

export function eventTone(priority) {
  if (priority === 'critical') return 'critical';
  if (priority === 'high') return 'warning';
  if (priority === 'medium') return 'info';
  return 'neutral';
}

export function deriveOperatorState(rawTap = {}, activeSession = null, recentEvents = []) {
  const tap = rawTap || {};
  const safeRecentEvents = Array.isArray(recentEvents) ? recentEvents : [];
  const problemEvent = safeRecentEvents.find((item) => reasonFromEvent(item));
  const staleHeartbeat = minutesSince(tap.last_heartbeat_at || tap.updated_at || activeSession?.lock_set_at || null);
  const isHeartbeatStale = staleHeartbeat != null && staleHeartbeat >= 5;

  if (!tap.keg_id) {
    return {
      state: TAP_OPERATOR_STATES.NO_KEG,
      reason: '\u041a\u0435\u0433\u0430 \u043d\u0435 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0430, \u043f\u0440\u043e\u0434\u0430\u0436\u0430 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430, \u043f\u043e\u043a\u0430 \u043b\u0438\u043d\u0438\u044e \u043d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0442.',
      telemetry: isHeartbeatStale ? `\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0441\u0438\u0433\u043d\u0430\u043b ${staleHeartbeat} \u043c\u0438\u043d. \u043d\u0430\u0437\u0430\u0434.` : null,
    };
  }

  if (tap.sync_state === 'syncing' || tap.status === 'processing_sync') {
    return {
      state: TAP_OPERATOR_STATES.SYNCING,
      reason: '\u041a\u0440\u0430\u043d \u0436\u0434\u0451\u0442 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0445 \u0434\u0430\u043d\u043d\u044b\u0445 \u043e\u0442 \u0441\u0435\u0440\u0432\u0435\u0440\u0430.',
      telemetry: activeSession ? '\u0415\u0441\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0432\u0438\u0437\u0438\u0442.' : null,
    };
  }

  if (activeSession || safeRecentEvents.some((item) => item.reason === 'authorized_pour_in_progress' || item.session_state === 'authorized_session')) {
    return {
      state: TAP_OPERATOR_STATES.POURING,
      reason: activeSession
        ? '\u0415\u0441\u0442\u044c \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0432\u0438\u0437\u0438\u0442, \u043d\u0430\u043b\u0438\u0432 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d.'
        : '\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 \u0443\u0436\u0435 \u0441\u043e\u043e\u0431\u0449\u0438\u043b \u043e \u043d\u0430\u0447\u0430\u043b\u0435 \u043d\u0430\u043b\u0438\u0432\u0430.',
      telemetry: activeSession?.card_uid ? `\u041a\u0430\u0440\u0442\u0430 ${activeSession.card_uid}` : null,
    };
  }

  if (tap.status === 'cleaning' || tap.status === 'empty' || tap.status === 'locked') {
    return {
      state: TAP_OPERATOR_STATES.UNAVAILABLE,
      reason: tap.status === 'locked'
        ? '\u041a\u0440\u0430\u043d \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d \u0438 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435 \u043f\u0440\u043e\u0434\u0430\u0451\u0442.'
        : tap.status === 'cleaning'
          ? '\u041a\u0440\u0430\u043d \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432 \u043f\u0440\u043e\u043c\u044b\u0432\u043a\u0435.'
          : '\u041b\u0438\u043d\u0438\u044f \u043f\u043e\u043c\u0435\u0447\u0435\u043d\u0430 \u043a\u0430\u043a \u043f\u0443\u0441\u0442\u0430\u044f \u0438 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u0441\u043d\u044f\u0442\u0430 \u0441 \u043f\u0440\u043e\u0434\u0430\u0436\u0438.',
      telemetry: isHeartbeatStale ? `\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0441\u0438\u0433\u043d\u0430\u043b ${staleHeartbeat} \u043c\u0438\u043d. \u043d\u0430\u0437\u0430\u0434.` : null,
    };
  }

  if (problemEvent || isHeartbeatStale) {
    return {
      state: TAP_OPERATOR_STATES.NEEDS_HELP,
      reason: problemEvent
        ? reasonFromEvent(problemEvent)
        : '\u0423\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u0434\u0430\u0432\u043d\u043e \u043d\u0435 \u043f\u0440\u0438\u0441\u044b\u043b\u0430\u043b\u043e heartbeat, \u043e\u043f\u0435\u0440\u0430\u0442\u043e\u0440\u0443 \u043d\u0443\u0436\u043d\u0430 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043b\u0438\u043d\u0438\u0438.',
      telemetry: isHeartbeatStale ? `\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 \u0441\u0438\u0433\u043d\u0430\u043b ${staleHeartbeat} \u043c\u0438\u043d. \u043d\u0430\u0437\u0430\u0434.` : null,
    };
  }

  if (tap.status === 'active' || tap.product_state === TAP_OPERATOR_STATES.READY) {
    return {
      state: TAP_OPERATOR_STATES.READY,
      reason: '\u0412\u0441\u0435 \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043e\u0442\u0432\u0435\u0447\u0430\u044e\u0442, \u043a\u0440\u0430\u043d \u043c\u043e\u0436\u043d\u043e \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u0434\u043b\u044f \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0439 \u043f\u0440\u043e\u0434\u0430\u0436\u0438.',
      telemetry: null,
    };
  }

  return {
    state: TAP_OPERATOR_STATES.NEEDS_HELP,
    reason: '\u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u043a\u0440\u0430\u043d\u0430 \u043d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0443\u0432\u0435\u0440\u0435\u043d\u043d\u043e \u043a\u043b\u0430\u0441\u0441\u0438\u0444\u0438\u0446\u0438\u0440\u043e\u0432\u0430\u0442\u044c, \u043d\u0443\u0436\u043d\u0430 \u0440\u0443\u0447\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430.',
    telemetry: null,
  };
}
