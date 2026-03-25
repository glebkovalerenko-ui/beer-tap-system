import {
  canonicalVisitStatusLabel,
  resolveCanonicalVisitStatus,
} from '../../lib/operator/visitStatus.js';

export const completionSourceLabels = {
  normal: 'Обычное завершение',
  card_removed: 'Карта извлечена',
  timeout: 'Таймаут / автоостановка',
  blocked: 'Заблокировано',
  denied: 'Отказано',
  no_sale_flow: 'Служебный налив без продажи',
  guest_checkout: 'Завершён расчётом гостя',
  checkout: 'Завершён расчётом',
  demo_checkout: 'Демонстрационное завершение',
  operator_close: 'Закрыт оператором',
  manual_close: 'Закрыт вручную',
  card_removed_close: 'Завершён после извлечения карты',
  controller_timeout: 'Таймаут контроллера',
  sync_timeout: 'Таймаут синхронизации',
  timeout_close: 'Завершён по таймауту',
  blocked_lost_card: 'Заблокировано: карта потеряна',
  blocked_insufficient_funds: 'Заблокировано: недостаточно средств',
  blocked_card_in_use: 'Заблокировано: карта уже используется на другом кране',
  denied_insufficient_funds: 'Отказано: недостаточно средств',
  sync_pending: 'Ожидает синхронизацию',
  system: 'Системное завершение',
};

export function normalizeVisit(item, source) {
  const lifecycle = item.lifecycle || {};
  const canonicalStatus = resolveCanonicalVisitStatus(item);
  const isActive = ['active', 'awaiting_action', 'pouring_now', 'needs_attention', 'blocked'].includes(canonicalStatus)
    && normalizeText(item.visit_status || item.status) === 'active';

  return {
    ...item,
    source,
    isActive,
    lifecycle,
    canonical_visit_status: canonicalStatus,
    opened_at: item.opened_at || lifecycle.opened_at || null,
    last_event_at: item.last_event_at || lifecycle.last_event_at || lifecycle.last_pour_ended_at || item.updated_at || null,
    guest_full_name: item.guest_full_name || 'Гость без имени',
    operator_status: item.operator_status || canonicalVisitStatusLabel(canonicalStatus),
    visit_status: item.visit_status || item.status || (isActive ? 'active' : null),
    taps: item.taps || (item.active_tap_id ? [String(item.active_tap_id)] : []),
    sync_state: item.sync_state || (isActive ? 'pending_sync' : 'not_started'),
    completion_source: item.completion_source ?? null,
    contains_tail_pour: Boolean(item.contains_tail_pour),
    contains_non_sale_flow: Boolean(item.contains_non_sale_flow),
    has_incident: Boolean(item.has_incident),
    has_unsynced: Boolean(item.has_unsynced),
    incident_count: item.incident_count || 0,
    card_uid: item.card_uid || '',
  };
}

export function mergeVisits(active = [], history = []) {
  const map = new Map();
  for (const item of history) map.set(String(item.visit_id), item);
  for (const item of active) {
    map.set(String(item.visit_id), { ...map.get(String(item.visit_id)), ...item, isActive: true, source: 'active' });
  }
  return Array.from(map.values()).sort((a, b) => {
    if (a.isActive !== b.isActive) return a.isActive ? -1 : 1;
    return new Date(b.last_event_at || b.opened_at || 0).getTime() - new Date(a.last_event_at || a.opened_at || 0).getTime();
  });
}

export function normalizeCompletionSource(item) {
  const raw = normalizeText(item?.completion_source);
  const actions = (item?.operator_actions || []).map((action) => normalizeText(action.action));

  if (item?.contains_non_sale_flow) return 'no_sale_flow';
  if (raw === 'card_removed' || raw === 'card_removed_close' || raw.includes('card_removed')) return 'card_removed';
  if (raw === 'timeout' || raw === 'timeout_close' || raw.endsWith('_timeout') || raw.includes('timeout')) return 'timeout';
  if (raw.startsWith('blocked_') || actions.some((action) => ['lost_card_blocked', 'insufficient_funds_blocked', 'card_in_use_on_other_tap'].includes(action))) {
    return 'blocked';
  }
  if (raw.startsWith('denied_') || actions.some((action) => action === 'insufficient_funds_denied')) {
    return 'denied';
  }
  if (raw === 'sync_pending' && item?.has_unsynced) return 'timeout';
  if (raw) return 'normal';
  if (resolveCanonicalVisitStatus(item) === 'blocked') return 'blocked';
  return item?.isActive ? '' : 'normal';
}

export function describeCompletionSource(value) {
  if (!value) return 'Не указана';
  return completionSourceLabels[value] || value.replaceAll('_', ' ');
}

export function describeCompletionSourceDetails(item) {
  const normalized = normalizeCompletionSource(item);
  const raw = String(item?.completion_source || '').trim();
  if (!normalized && !raw) return 'Не указана';
  if (raw && raw !== normalized) return `${describeCompletionSource(normalized)} · ${describeCompletionSource(raw.toLowerCase())}`;
  return describeCompletionSource(raw || normalized);
}

export function isZeroVolumeAbort(item) {
  return resolveCanonicalVisitStatus(item) === 'blocked' && !item.lifecycle?.first_pour_started_at && !item.lifecycle?.last_pour_ended_at;
}

export function describeFlags(item) {
  const flags = [];
  if (item.contains_tail_pour) flags.push('Есть долив хвоста');
  if (item.contains_non_sale_flow) flags.push('Есть служебный налив без продажи');
  if (item.has_incident) flags.push(`Есть инциденты (${item.incident_count || 1})`);
  if (item.has_unsynced) flags.push('Есть несинхронизированные данные');
  return flags.length ? flags.join(' · ') : 'Особых флагов нет';
}

function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}
