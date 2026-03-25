import test from 'node:test';
import assert from 'node:assert/strict';

import { buildSessionBadges } from './sessionBadgeModel.js';

test('buildSessionBadges prioritizes operator badges for active and problematic sessions', () => {
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
    ['active', 'incident', 'unsynced', 'sync-state'],
  );
});

test('buildSessionBadges adds zero-volume abort and secondary flags when present', () => {
  const badges = buildSessionBadges(
    {
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
    ['Прервана без налива', 'Служебный налив', 'Есть долив хвоста', 'Синхронизирована'],
  );
});
