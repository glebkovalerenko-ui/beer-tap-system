import { matchesSessionDateRange, resolveDateBounds } from './sessionDateFilters.js';
import { isZeroVolumeAbort, normalizeCompletionSource } from './sessionNormalize.js';

export function matchesText(item, query) {
  const normalized = String(query || '').trim().toLowerCase();
  if (!normalized) return true;
  return [item.card_uid, item.visit_id, item.guest_full_name]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(normalized));
}

export function matchesStatus(item, status) {
  if (!status) return true;
  if (status === 'active') return item.isActive;
  if (status === 'closed') return !item.isActive && item.operator_status !== 'Прервана';
  if (status === 'aborted') return item.operator_status === 'Прервана';
  return true;
}

export function matchesSessionFilters(item, filters, getPeriodBounds) {
  const dateBounds = resolveDateBounds(filters, getPeriodBounds);
  if (!matchesSessionDateRange(item, dateBounds)) return false;
  if (filters.tapId) {
    const tapNeedle = String(filters.tapId).trim();
    const taps = (item.taps || []).map((tap) => String(tap));
    if (!taps.includes(tapNeedle)) return false;
  }
  if (!matchesStatus(item, filters.status)) return false;
  if (!matchesText(item, filters.cardUid)) return false;
  if (filters.completionSource && normalizeCompletionSource(item) !== filters.completionSource) return false;
  if (filters.incidentOnly && !item.has_incident) return false;
  if (filters.unsyncedOnly && !item.has_unsynced) return false;
  if (filters.zeroVolumeAbortOnly && !isZeroVolumeAbort(item)) return false;
  if (filters.activeOnly && !item.isActive) return false;
  return true;
}
