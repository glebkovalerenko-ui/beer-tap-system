import { canonicalVisitStatusLabel, canonicalVisitStatusTone, resolveCanonicalVisitStatus } from './visitStatus.js';

export function buildSessionBadges(item, { syncLabels, isZeroVolumeAbort }) {
  const badges = [];
  const canonicalStatus = resolveCanonicalVisitStatus(item);

  badges.push({
    key: 'visit-status',
    label: canonicalVisitStatusLabel(canonicalStatus),
    tone: canonicalVisitStatusTone(canonicalStatus),
  });

  if (item?.has_incident) {
    badges.push({
      key: 'incident',
      label: item.incident_count ? `Инциденты: ${item.incident_count}` : 'Есть инцидент',
      tone: 'warning',
    });
  }

  if (item?.has_unsynced) {
    badges.push({
      key: 'unsynced',
      label: 'Нужна синхронизация',
      tone: 'warning',
    });
  }

  if (isZeroVolumeAbort?.(item)) {
    badges.push({
      key: 'zero-volume-abort',
      label: 'Прерван без налива',
      tone: 'muted',
    });
  }

  if (item?.contains_non_sale_flow) {
    badges.push({
      key: 'non-sale-flow',
      label: 'Служебный налив',
      tone: 'muted',
    });
  }

  if (item?.contains_tail_pour) {
    badges.push({
      key: 'tail-pour',
      label: 'Есть долив хвоста',
      tone: 'muted',
    });
  }

  if (item?.sync_state) {
    badges.push({
      key: 'sync-state',
      label: syncLabels?.[item.sync_state] || item.sync_state,
      tone: item?.has_unsynced ? 'warning' : 'neutral',
    });
  }

  return badges;
}
