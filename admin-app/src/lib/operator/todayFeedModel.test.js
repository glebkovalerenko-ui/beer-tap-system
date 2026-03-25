import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTodayFeedItems } from './todayFeedModel.js';

test('buildTodayFeedItems prioritizes critical incidents above neutral events', () => {
  const items = buildTodayFeedItems([
    {
      item_id: 'ok-1',
      item_type: 'pour',
      status: 'accepted',
      tap_id: 1,
      volume_ml: 500,
      ended_at: '2026-03-25T12:00:00.000Z',
    },
    {
      item_id: 'critical-1',
      item_type: 'flow_event',
      tap_id: 2,
      volume_ml: 120,
      reason: 'flow_detected_when_valve_closed_without_active_session',
      timestamp: '2026-03-25T12:01:00.000Z',
    },
  ]);

  assert.deepEqual(items.map((item) => item.item_id), ['critical-1', 'ok-1']);
  assert.equal(items[0].severity, 'critical');
});

test('buildTodayFeedItems maps rejected pours to warning severity', () => {
  const items = buildTodayFeedItems([
    {
      item_id: 'pour-1',
      item_type: 'pour',
      status: 'rejected',
      tap_id: 7,
      volume_ml: 330,
      beverage_name: 'Pilsner',
      ended_at: '2026-03-25T12:02:00.000Z',
    },
  ]);

  assert.equal(items[0].severity, 'warning');
  assert.equal(items[0].badgeLabel, 'Нужна проверка');
});
