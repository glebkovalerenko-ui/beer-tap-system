import test from 'node:test';
import assert from 'node:assert/strict';

import { matchesSessionDateRange, resolveDateBounds } from './sessionDateFilters.js';

test('resolveDateBounds uses getPeriodBounds for today/shift and raw values for range', () => {
  const filters = { periodPreset: 'shift', dateFrom: '', dateTo: '' };
  const bounds = resolveDateBounds(filters, (preset) => {
    assert.equal(preset, 'shift');
    return { dateFrom: '2026-03-20', dateTo: '2026-03-22' };
  });

  assert.equal(bounds.start.toISOString(), '2026-03-20T00:00:00.000Z');
  assert.equal(bounds.end.toISOString(), '2026-03-22T23:59:59.999Z');

  const rangeBounds = resolveDateBounds(
    { periodPreset: 'range', dateFrom: '2026-03-10', dateTo: '2026-03-10' },
    () => {
      throw new Error('should not be called for range preset');
    }
  );

  assert.equal(rangeBounds.start.toISOString(), '2026-03-10T00:00:00.000Z');
  assert.equal(rangeBounds.end.toISOString(), '2026-03-10T23:59:59.999Z');
});

test('active session stays visible when backend history is filtered to a day inside active interval', () => {
  const bounds = resolveDateBounds(
    { periodPreset: 'range', dateFrom: '2026-03-10', dateTo: '2026-03-10' },
    () => ({})
  );
  const now = new Date('2026-03-24T10:00:00.000Z');

  // Typical UI merge case: backend returns only history for the selected day,
  // but active visits are merged on top by the frontend.
  const backendHistoryItem = {
    visit_id: 'history-1',
    opened_at: '2026-03-10T08:00:00.000Z',
    last_event_at: '2026-03-10T09:00:00.000Z',
    isActive: false,
  };

  const activeItem = {
    visit_id: 'active-1',
    opened_at: '2026-03-01T08:00:00.000Z',
    last_event_at: '2026-03-24T09:30:00.000Z',
    isActive: true,
  };

  assert.equal(matchesSessionDateRange(backendHistoryItem, bounds, now), true);
  assert.equal(matchesSessionDateRange(activeItem, bounds, now), true);
});

test('session outside range is excluded', () => {
  const bounds = resolveDateBounds(
    { periodPreset: 'range', dateFrom: '2026-03-10', dateTo: '2026-03-10' },
    () => ({})
  );

  const closedOutsideRange = {
    opened_at: '2026-03-11T08:00:00.000Z',
    last_event_at: '2026-03-11T09:00:00.000Z',
    isActive: false,
  };

  assert.equal(matchesSessionDateRange(closedOutsideRange, bounds), false);
});
