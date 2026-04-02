import test from 'node:test';
import assert from 'node:assert/strict';

import { normalizeOperatorActionPolicy, resolveActionBlockState } from './actionPolicyAdapter.js';

test('normalizeOperatorActionPolicy blocks second approval flows in the current UI', () => {
  const policy = normalizeOperatorActionPolicy({
    allowed: true,
    confirm_required: true,
    second_approval_required: true,
  });

  assert.equal(policy.allowed, false);
  assert.equal(policy.rawAllowed, true);
  assert.equal(policy.confirmRequired, true);
  assert.equal(policy.secondApprovalRequired, true);
  assert.match(policy.disabledReason || '', /второе согласование/i);
});

test('normalizeOperatorActionPolicy supports legacy enabled and reason code flags', () => {
  const policy = normalizeOperatorActionPolicy({
    enabled: false,
    reason_code_required: true,
    reason: 'Operator role required.',
  });

  assert.equal(policy.allowed, false);
  assert.equal(policy.reasonCodeRequired, true);
  assert.equal(policy.disabledReason, 'Operator role required.');
});

test('resolveActionBlockState lets read-only reason override an allowed policy', () => {
  const state = resolveActionBlockState(
    { allowed: true, confirm_required: true },
    'Backend degraded. Try again later.'
  );

  assert.equal(state.disabled, true);
  assert.equal(state.reason, 'Backend degraded. Try again later.');
  assert.equal(state.policy.allowed, false);
  assert.equal(state.policy.disabledReason, 'Backend degraded. Try again later.');
});
