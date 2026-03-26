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

test('buildTapQuickActions explains why stop is unavailable without an active visit', () => {
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
  assert.match(actions.find((action) => action.id === 'stop')?.reason || '', /нет активного визита/i);
  assert.equal(actions.find((action) => action.id === 'toggle-lock')?.disabled, false);
});

test('buildTapQuickActions prefers backend safe action policies over local fallbacks', () => {
  const actions = buildTapQuickActions({
    tap: {
      tap_id: 4,
      display_name: 'Tap 4',
      status: 'active',
      safe_actions: {
        stop: { allowed: false, disabled_reason: 'Reader is offline.' },
        block: { allowed: false, disabled_reason: 'Read-only snapshot.' },
        history: { allowed: true },
      },
    },
    session: { visitId: 'v-4' },
    permissions: {
      taps_control: true,
      display_override: true,
    },
    canControl: true,
    canDisplayOverride: true,
  });

  assert.equal(actions.find((action) => action.id === 'stop')?.disabled, true);
  assert.equal(actions.find((action) => action.id === 'stop')?.reason, 'Reader is offline.');
  assert.equal(actions.find((action) => action.id === 'toggle-lock')?.disabled, true);
  assert.equal(actions.find((action) => action.id === 'toggle-lock')?.reason, 'Read-only snapshot.');
  assert.equal(actions.find((action) => action.id === 'history')?.disabled, false);
});
