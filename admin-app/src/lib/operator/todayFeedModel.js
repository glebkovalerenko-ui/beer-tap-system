import {
  formatDurationRu,
  formatRubAmount,
  formatVolumeRu,
} from '../formatters.js';

const SEVERITY_WEIGHT = Object.freeze({
  critical: 0,
  warning: 1,
  info: 2,
  neutral: 3,
});

function eventAt(item) {
  return item?.ended_at || item?.timestamp || item?.poured_at || item?.created_at || item?.started_at || '';
}

function dismissKey(item) {
  return item?.item_id || item?.id || `${item?.item_type || 'event'}-${eventAt(item)}-${item?.tap_id ?? 'na'}`;
}

function eventTimeValue(item) {
  const value = new Date(item?.eventAt || eventAt(item)).getTime();
  return Number.isNaN(value) ? 0 : value;
}

function tapLabel(item) {
  return item?.tap_name || (item?.tap_id != null ? `\u041a\u0440\u0430\u043d #${item.tap_id}` : '\u041a\u0440\u0430\u043d \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d');
}

function buildMetric(item) {
  if (item?.item_type === 'pour' && item?.amount_charged != null) {
    return `-${formatRubAmount(item.amount_charged)}`;
  }

  if (item?.volume_ml != null) {
    return formatVolumeRu(item.volume_ml);
  }

  return null;
}

function buildMappedFeedItem(item) {
  const tap = tapLabel(item);
  const metric = buildMetric(item);

  if (item?.reason === 'flow_detected_when_valve_closed_without_active_session') {
    return {
      ...item,
      eventAt: eventAt(item),
      dismissKey: dismissKey(item),
      severity: 'critical',
      severityLabel: '\u041a\u0440\u0438\u0442\u0438\u0447\u043d\u043e',
      category: item?.card_present ? '\u041a\u043b\u0430\u043f\u0430\u043d / \u043f\u043e\u0442\u043e\u043a' : '\u041f\u0440\u043e\u043b\u0438\u0432 \u0431\u0435\u0437 \u043a\u0430\u0440\u0442\u044b',
      headline: item?.card_present
        ? '\u041f\u0440\u043e\u043b\u0438\u0432 \u043f\u0440\u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u043e\u043c \u043a\u043b\u0430\u043f\u0430\u043d\u0435'
        : '\u041f\u0440\u043e\u043b\u0438\u0432 \u0431\u0435\u0437 \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0439 \u0441\u0435\u0441\u0441\u0438\u0438',
      detail: `${tap}${metric ? ` \u00b7 ${metric}` : ''} \u00b7 \u041d\u0443\u0436\u043d\u0430 \u043d\u0435\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u0430\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043d\u0430 \u0442\u043e\u0447\u043a\u0435`,
      badgeLabel: '\u0422\u0440\u0435\u0431\u0443\u0435\u0442 \u0432\u043c\u0435\u0448\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430',
      metric,
    };
  }

  if (item?.item_type === 'pour') {
    const accepted = item?.status !== 'rejected';
    const beverage = item?.beverage_name || '\u043d\u0430\u043f\u0438\u0442\u043e\u043a';
    return {
      ...item,
      eventAt: eventAt(item),
      dismissKey: dismissKey(item),
      severity: accepted ? 'neutral' : 'warning',
      severityLabel: accepted ? '\u041d\u043e\u0440\u043c\u0430' : '\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435',
      category: accepted ? '\u041f\u0440\u043e\u0434\u0430\u0436\u0430' : '\u041f\u0440\u043e\u0434\u0430\u0436\u0430 / \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0438\u0435',
      headline: accepted ? '\u041d\u0430\u043b\u0438\u0432 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d' : '\u041f\u0440\u043e\u0434\u0430\u0436\u0430 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0430',
      detail: `${tap} \u00b7 ${formatVolumeRu(item.volume_ml || 0)} ${beverage}${item.duration_ms != null ? ` \u00b7 ${formatDurationRu(item.duration_ms)}` : ''}`,
      badgeLabel: accepted ? '\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u043e' : '\u041d\u0443\u0436\u043d\u0430 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430',
      metric,
    };
  }

  if (item?.reason === 'authorized_pour_in_progress' || item?.session_state === 'authorized_session') {
    const isStopped = item?.event_status === 'stopped';
    return {
      ...item,
      eventAt: eventAt(item),
      dismissKey: dismissKey(item),
      severity: isStopped ? 'neutral' : 'info',
      severityLabel: isStopped ? '\u041d\u043e\u0440\u043c\u0430' : '\u0412 \u0440\u0430\u0431\u043e\u0442\u0435',
      category: '\u0416\u0438\u0432\u043e\u0439 \u043d\u0430\u043b\u0438\u0432',
      headline: isStopped
        ? '\u041d\u0430\u043b\u0438\u0432 \u043f\u043e \u0441\u0435\u0441\u0441\u0438\u0438 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d'
        : '\u0418\u0434\u0451\u0442 \u043d\u0430\u043b\u0438\u0432 \u043f\u043e \u0441\u0435\u0441\u0441\u0438\u0438',
      detail: `${tap}${metric ? ` \u00b7 ${metric}` : ''} \u00b7 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u0435\u0442 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u043f\u043e\u0442\u043e\u043a`,
      badgeLabel: isStopped ? '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d' : '\u041b\u044c\u0451\u0442',
      metric,
    };
  }

  if (item?.event_status === 'started') {
    return {
      ...item,
      eventAt: eventAt(item),
      dismissKey: dismissKey(item),
      severity: 'warning',
      severityLabel: '\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435',
      category: '\u041f\u043e\u0442\u043e\u043a',
      headline: '\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043b \u043f\u043e\u0442\u043e\u043a',
      detail: `${tap}${metric ? ` \u00b7 ${metric}` : ''} \u00b7 \u0441\u0442\u043e\u0438\u0442 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c, \u0447\u0442\u043e \u0441\u0435\u0441\u0441\u0438\u044f \u0438 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u044b`,
      badgeLabel: '\u0422\u0440\u0435\u0431\u0443\u0435\u0442 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438',
      metric,
    };
  }

  if (item?.event_status === 'stopped') {
    return {
      ...item,
      eventAt: eventAt(item),
      dismissKey: dismissKey(item),
      severity: 'neutral',
      severityLabel: '\u041d\u043e\u0440\u043c\u0430',
      category: '\u041f\u043e\u0442\u043e\u043a',
      headline: '\u041f\u043e\u0442\u043e\u043a \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d',
      detail: `${tap}${metric ? ` \u00b7 ${metric}` : ''} \u00b7 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 \u043f\u0435\u0440\u0435\u0434\u0430\u043b \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0443 \u043f\u0440\u043e\u043b\u0438\u0432\u0430`,
      badgeLabel: '\u041e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d',
      metric,
    };
  }

  return {
    ...item,
    eventAt: eventAt(item),
    dismissKey: dismissKey(item),
    severity: 'neutral',
    severityLabel: '\u041d\u043e\u0440\u043c\u0430',
    category: '\u041e\u0431\u0449\u0435\u0435',
    headline: tap,
    detail: item?.reason || item?.status || item?.event_status || '\u0421\u043e\u0431\u044b\u0442\u0438\u0435 \u043f\u043e\u0441\u0442\u0443\u043f\u0438\u043b\u043e \u0431\u0435\u0437 \u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u044f.',
    badgeLabel: '\u041e\u0431\u0449\u0435\u0435',
    metric,
  };
}

export function sortTodayFeedItems(left, right) {
  const severityDiff = (SEVERITY_WEIGHT[left.severity] ?? 9) - (SEVERITY_WEIGHT[right.severity] ?? 9);
  if (severityDiff !== 0) {
    return severityDiff;
  }

  return eventTimeValue(right) - eventTimeValue(left);
}

export function buildTodayFeedItems(items = [], { dismissedEventIds = new Set(), limit = 12 } = {}) {
  return (items || [])
    .filter((item) => !dismissedEventIds.has(dismissKey(item)))
    .map((item) => buildMappedFeedItem(item))
    .sort(sortTodayFeedItems)
    .slice(0, limit);
}
