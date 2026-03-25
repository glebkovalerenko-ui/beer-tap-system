import test from 'node:test';
import assert from 'node:assert/strict';

import {
  TAP_OPERATOR_STATES,
  deriveOperatorState,
} from './tapStateModel.js';

test('deriveOperatorState returns no_keg when tap has no keg', () => {
  const result = deriveOperatorState({ tap_id: 1, status: 'active', keg_id: null }, null, []);
  assert.equal(result.state, TAP_OPERATOR_STATES.NO_KEG);
});

test('deriveOperatorState returns pouring for active authorized session', () => {
  const result = deriveOperatorState(
    { tap_id: 2, status: 'active', keg_id: 20 },
    { visit_id: 'v-1', card_uid: 'uid-1' },
    [],
  );

  assert.equal(result.state, TAP_OPERATOR_STATES.POURING);
});

test('deriveOperatorState returns needs_help for abnormal flow event', () => {
  const result = deriveOperatorState(
    { tap_id: 3, status: 'active', keg_id: 30 },
    null,
    [{ reason: 'flow_detected_when_valve_closed_without_active_session' }],
  );

  assert.equal(result.state, TAP_OPERATOR_STATES.NEEDS_HELP);
});

test('deriveOperatorState returns unavailable for locked tap', () => {
  const result = deriveOperatorState({ tap_id: 4, status: 'locked', keg_id: 40 }, null, []);
  assert.equal(result.state, TAP_OPERATOR_STATES.UNAVAILABLE);
});

test('deriveOperatorState returns ready for active tap with healthy context', () => {
  const result = deriveOperatorState({ tap_id: 5, status: 'active', keg_id: 50 }, null, []);
  assert.equal(result.state, TAP_OPERATOR_STATES.READY);
});
