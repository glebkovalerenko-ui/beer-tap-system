import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTapQuickActions } from './tapQuickActions.js';

test('buildTapQuickActions returns ordered operator actions for active tap', () => {
  const actions = buildTapQuickActions({
    tap: { tap_id: 11, display_name: 'Кран 11', status: 'active', keg_id: 99 },
    session: { visitId: 'v-11' },
    permissions: {
      taps_control: true,
      display_override: true,
    },
    canControl: true,
    canDisplayOverride: true,
  });

  assert.deepEqual(actions.map((action) => action.id), ['open', 'stop', 'toggle-lock', 'screen', 'keg', 'history']);
  assert.equal(actions.find((action) => action.id === 'stop')?.disabled, false);
  assert.equal(actions.find((action) => action.id === 'screen')?.disabled, false);
});

test('buildTapQuickActions explains why stop and lock are unavailable', () => {
  const actions = buildTapQuickActions({
    tap: { tap_id: 7, display_name: 'Кран 7', status: 'active', keg_id: null },
    session: null,
    permissions: {
      taps_control: true,
      display_override: false,
    },
    canControl: true,
    canDisplayOverride: false,
  });

  assert.deepEqual(actions.map((action) => action.id), ['open', 'stop', 'toggle-lock', 'keg', 'history']);
  assert.match(actions.find((action) => action.id === 'stop')?.reason || '', /нет активной сессии/i);
  assert.match(actions.find((action) => action.id === 'toggle-lock')?.reason || '', /нет кеги/i);
});
