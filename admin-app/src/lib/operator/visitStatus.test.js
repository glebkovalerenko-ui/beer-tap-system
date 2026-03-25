import test from 'node:test';
import assert from 'node:assert/strict';

import { canonicalVisitStatusLabel, resolveCanonicalVisitStatus } from './visitStatus.js';

test('resolveCanonicalVisitStatus prefers attention states for incidents and unsynced visits', () => {
  assert.equal(
    resolveCanonicalVisitStatus({ has_incident: true, has_unsynced: true, visit_status: 'active' }),
    'needs_attention',
  );
});

test('resolveCanonicalVisitStatus maps active taps to pouring_now', () => {
  assert.equal(
    resolveCanonicalVisitStatus({ visit_status: 'active', active_tap_id: 3 }),
    'pouring_now',
  );
});

test('canonicalVisitStatusLabel returns operator-facing copy', () => {
  assert.equal(canonicalVisitStatusLabel('blocked'), 'Заблокирован');
});
