import test from 'node:test';
import assert from 'node:assert/strict';

import { buildSessionBadges } from './sessionBadgeModel.js';

test('buildSessionBadges prioritizes canonical visit status for problematic active visits', () => {
  const badges = buildSessionBadges(
    {
      isActive: true,
      has_incident: true,
      incident_count: 2,
      has_unsynced: true,
      sync_state: 'pending_sync',
    },
    {
      syncLabels: { pending_sync: 'Ожидает синхронизации' },
      isZeroVolumeAbort: () => false,
    },
  );

  assert.deepEqual(
    badges.map((badge) => badge.key),
    ['visit-status', 'incident', 'unsynced', 'sync-state'],
  );
  assert.equal(badges[0]?.label, 'Требует внимания');
});

test('buildSessionBadges keeps canonical visit badge and secondary flags for zero-volume aborts', () => {
  const badges = buildSessionBadges(
    {
      visit_status: 'completed',
      contains_non_sale_flow: true,
      contains_tail_pour: true,
      sync_state: 'synced',
    },
    {
      syncLabels: { synced: 'Синхронизирована' },
      isZeroVolumeAbort: () => true,
    },
  );

  assert.deepEqual(
    badges.map((badge) => badge.label),
    ['Завершён', 'Прерван без налива', 'Служебный налив', 'Есть долив хвоста', 'Синхронизирована'],
  );
});
