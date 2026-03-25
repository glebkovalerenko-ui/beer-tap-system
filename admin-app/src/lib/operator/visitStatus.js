const STATUS_META = Object.freeze({
  active: { label: 'Активен', tone: 'neutral' },
  awaiting_action: { label: 'Ожидает действия', tone: 'warning' },
  pouring_now: { label: 'Льёт сейчас', tone: 'info' },
  completed: { label: 'Завершён', tone: 'neutral' },
  needs_attention: { label: 'Требует внимания', tone: 'warning' },
  blocked: { label: 'Заблокирован', tone: 'critical' },
});

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

export function resolveCanonicalVisitStatus(item = {}) {
  const explicit = normalizeText(item.canonical_visit_status || item.canonicalVisitStatus);
  if (STATUS_META[explicit]) {
    return explicit;
  }

  const operatorStatus = normalizeText(item.operator_status || item.operatorStatus);
  const visitStatus = normalizeText(item.visit_status || item.visitStatus || item.status);
  const completionSource = normalizeText(item.completion_source || item.completionSource);
  const hasIncident = Boolean(item.has_incident ?? item.hasIncident);
  const hasUnsynced = Boolean(item.has_unsynced ?? item.hasUnsynced);
  const hasActiveTap = item.active_tap_id != null
    || item.activeTapId != null
    || (Array.isArray(item.taps) && item.taps.length > 0 && visitStatus === 'active');

  if (completionSource === 'blocked' || operatorStatus === 'заблокирован' || operatorStatus === 'прервана') {
    return 'blocked';
  }
  if (
    completionSource === 'timeout'
    || completionSource === 'denied'
    || completionSource === 'no_sale_flow'
    || hasIncident
    || hasUnsynced
    || operatorStatus === 'требует внимания'
  ) {
    return 'needs_attention';
  }
  if (visitStatus && visitStatus !== 'active') {
    return 'completed';
  }
  if (operatorStatus === 'льёт сейчас' || hasActiveTap) {
    return 'pouring_now';
  }
  if (operatorStatus === 'ожидает действия') {
    return 'awaiting_action';
  }
  return 'active';
}

export function canonicalVisitStatusMeta(value) {
  const key = resolveCanonicalVisitStatus({ canonical_visit_status: value });
  return STATUS_META[key] || STATUS_META.active;
}

export function canonicalVisitStatusLabel(value) {
  return canonicalVisitStatusMeta(value).label;
}

export function canonicalVisitStatusTone(value) {
  return canonicalVisitStatusMeta(value).tone;
}
