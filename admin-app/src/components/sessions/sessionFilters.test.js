import test from 'node:test';
import assert from 'node:assert/strict';

import { matchesSessionFilters } from './sessionFilters.js';

const PERIOD_FILTER = {
  periodPreset: 'range',
  dateFrom: '2026-03-24',
  dateTo: '2026-03-24',
  tapId: '',
  status: '',
  cardUid: '',
  completionSource: '',
  incidentOnly: false,
  unsyncedOnly: false,
  zeroVolumeAbortOnly: false,
  activeOnly: false,
};

function getPeriodBounds() {
  return { dateFrom: '2026-03-24', dateTo: '2026-03-24' };
}

test('matchesSessionFilters handles incidentOnly and unsyncedOnly flags', () => {
  const baseItem = {
    visit_id: 'v-1',
    opened_at: '2026-03-24T08:00:00.000Z',
    last_event_at: '2026-03-24T08:10:00.000Z',
    taps: ['1'],
    operator_status: 'Завершена',
    isActive: false,
    has_incident: true,
    has_unsynced: false,
    lifecycle: {},
  };

  assert.equal(matchesSessionFilters(baseItem, { ...PERIOD_FILTER, incidentOnly: true }, getPeriodBounds), true);
  assert.equal(matchesSessionFilters(baseItem, { ...PERIOD_FILTER, unsyncedOnly: true }, getPeriodBounds), false);
  assert.equal(
    matchesSessionFilters({ ...baseItem, has_unsynced: true }, { ...PERIOD_FILTER, incidentOnly: true, unsyncedOnly: true }, getPeriodBounds),
    true
  );
});

test('matchesSessionFilters applies completion source normalization filter', () => {
  const item = {
    visit_id: 'v-2',
    opened_at: '2026-03-24T08:00:00.000Z',
    last_event_at: '2026-03-24T08:10:00.000Z',
    taps: ['1'],
    operator_status: 'Завершена',
    completion_source: 'blocked_lost_card',
    isActive: false,
    lifecycle: {},
  };

  assert.equal(matchesSessionFilters(item, { ...PERIOD_FILTER, completionSource: 'blocked' }, getPeriodBounds), true);
  assert.equal(matchesSessionFilters(item, { ...PERIOD_FILTER, completionSource: 'denied' }, getPeriodBounds), false);
});
