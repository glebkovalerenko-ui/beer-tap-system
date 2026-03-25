import test from 'node:test';
import assert from 'node:assert/strict';

import { matchesSessionDateRange, resolveDateBounds } from './sessionDateFilters.js';

test('resolveDateBounds uses getPeriodBounds for today/shift and raw values for range', () => {
  const filters = { periodPreset: 'shift', dateFrom: '', dateTo: '' };
  const bounds = resolveDateBounds(filters, (preset) => {
    assert.equal(preset, 'shift');
    return { dateFrom: '2026-03-20', dateTo: '2026-03-22' };
  });

  assert.equal(bounds.start.getFullYear(), 2026);
  assert.equal(bounds.start.getMonth(), 2);
  assert.equal(bounds.start.getDate(), 20);
  assert.equal(bounds.start.getHours(), 0);
  assert.equal(bounds.start.getMinutes(), 0);
  assert.equal(bounds.start.getSeconds(), 0);
  assert.equal(bounds.start.getMilliseconds(), 0);

  assert.equal(bounds.end.getFullYear(), 2026);
  assert.equal(bounds.end.getMonth(), 2);
  assert.equal(bounds.end.getDate(), 22);
  assert.equal(bounds.end.getHours(), 23);
  assert.equal(bounds.end.getMinutes(), 59);
  assert.equal(bounds.end.getSeconds(), 59);
  assert.equal(bounds.end.getMilliseconds(), 999);

  const rangeBounds = resolveDateBounds(
    { periodPreset: 'range', dateFrom: '2026-03-10', dateTo: '2026-03-10' },
    () => {
      throw new Error('should not be called for range preset');
    }
  );

  assert.equal(rangeBounds.start.getFullYear(), 2026);
  assert.equal(rangeBounds.start.getMonth(), 2);
  assert.equal(rangeBounds.start.getDate(), 10);
  assert.equal(rangeBounds.start.getHours(), 0);
  assert.equal(rangeBounds.end.getHours(), 23);
  assert.equal(rangeBounds.end.getMinutes(), 59);
  assert.equal(rangeBounds.end.getSeconds(), 59);
  assert.equal(rangeBounds.end.getMilliseconds(), 999);
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
