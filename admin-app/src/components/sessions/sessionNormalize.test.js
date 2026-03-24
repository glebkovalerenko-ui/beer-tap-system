import test from 'node:test';
import assert from 'node:assert/strict';

import { isZeroVolumeAbort, mergeVisits, normalizeCompletionSource } from './sessionNormalize.js';

test('normalizeCompletionSource maps key completion branches', () => {
  assert.equal(normalizeCompletionSource({ completion_source: 'blocked_insufficient_funds' }), 'blocked');
  assert.equal(normalizeCompletionSource({ completion_source: 'denied_insufficient_funds' }), 'denied');
  assert.equal(normalizeCompletionSource({ completion_source: 'sync_timeout' }), 'timeout');
  assert.equal(normalizeCompletionSource({ completion_source: 'card_removed_close' }), 'card_removed');
  assert.equal(normalizeCompletionSource({ contains_non_sale_flow: true, completion_source: 'checkout' }), 'no_sale_flow');
});

test('isZeroVolumeAbort returns true only for aborted sessions with no pour timestamps', () => {
  assert.equal(
    isZeroVolumeAbort({
      operator_status: 'Прервана',
      lifecycle: { first_pour_started_at: null, last_pour_ended_at: null },
    }),
    true
  );

  assert.equal(
    isZeroVolumeAbort({
      operator_status: 'Прервана',
      lifecycle: { first_pour_started_at: '2026-03-24T10:00:00.000Z', last_pour_ended_at: null },
    }),
    false
  );
});

test('mergeVisits keeps active record over history and sorts active first', () => {
  const merged = mergeVisits(
    [
      { visit_id: '10', isActive: true, source: 'active', guest_full_name: 'Active Guest', last_event_at: '2026-03-24T10:00:00.000Z' },
    ],
    [
      { visit_id: '9', isActive: false, source: 'history', guest_full_name: 'History Guest', last_event_at: '2026-03-24T09:00:00.000Z' },
      { visit_id: '10', isActive: false, source: 'history', guest_full_name: 'Stale Name', last_event_at: '2026-03-24T08:00:00.000Z' },
    ]
  );

  assert.equal(merged.length, 2);
  assert.equal(merged[0].visit_id, '10');
  assert.equal(merged[0].guest_full_name, 'Active Guest');
  assert.equal(merged[0].source, 'active');
  assert.equal(merged[1].visit_id, '9');
});
