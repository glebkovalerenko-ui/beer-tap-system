const STATUS_META = Object.freeze({
  success: { label: 'Успешно', tone: 'success' },
  stopped: { label: 'Остановлен', tone: 'muted' },
  timeout: { label: 'Таймаут', tone: 'warning' },
  card_removed: { label: 'Карта убрана', tone: 'warning' },
  denied: { label: 'Отклонён', tone: 'critical' },
  non_sale: { label: 'Без продажи', tone: 'info' },
  error: { label: 'Ошибка', tone: 'critical' },
});

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

function toNumber(value) {
  if (value == null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function resolveCanonicalPourStatus(item = {}) {
  const explicit = normalizeText(item.canonical_pour_status || item.canonicalPourStatus);
  if (STATUS_META[explicit]) {
    return explicit;
  }

  const rawStatus = normalizeText(item.status);
  const completionReason = normalizeText(item.completion_reason || item.completionReason);
  const saleKind = normalizeText(item.sale_kind || item.saleKind);
  const amountCharged = toNumber(item.amount_charged ?? item.amountCharged ?? item.amount);
  const volumeMl = toNumber(item.volume_ml ?? item.volumeMl);

  if (saleKind === 'non_sale' || rawStatus === 'non_sale' || completionReason.includes('non_sale') || completionReason.includes('no_sale')) {
    return 'non_sale';
  }

  if (
    rawStatus === 'denied'
    || rawStatus === 'rejected'
    || completionReason.startsWith('denied')
    || completionReason.includes('insufficient_funds')
  ) {
    return 'denied';
  }

  if (completionReason.includes('card_removed')) {
    return 'card_removed';
  }

  if (rawStatus === 'timeout' || completionReason.includes('timeout')) {
    return 'timeout';
  }

  if (rawStatus === 'attention' || rawStatus === 'error' || completionReason.includes('error') || completionReason.includes('fault')) {
    return 'error';
  }

  if (rawStatus === 'zero_volume' || rawStatus === 'stopped' || rawStatus === 'aborted') {
    return 'stopped';
  }

  if (rawStatus === 'completed' || rawStatus === 'accepted' || amountCharged != null || (volumeMl != null && volumeMl > 0)) {
    return 'success';
  }

  return 'stopped';
}

export function canonicalPourStatusMeta(value) {
  const key = resolveCanonicalPourStatus({ canonical_pour_status: value });
  return STATUS_META[key] || STATUS_META.success;
}

export function canonicalPourStatusLabel(value) {
  return canonicalPourStatusMeta(value).label;
}

export function canonicalPourStatusTone(value) {
  return canonicalPourStatusMeta(value).tone;
}
