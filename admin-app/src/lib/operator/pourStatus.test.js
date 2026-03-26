import test from 'node:test';
import assert from 'node:assert/strict';

import { canonicalPourStatusLabel, resolveCanonicalPourStatus } from './pourStatus.js';

test('resolveCanonicalPourStatus maps successful pours from charged and volume signals', () => {
  assert.equal(resolveCanonicalPourStatus({ status: 'completed', amount_charged: 220, volume_ml: 500 }), 'success');
});

test('resolveCanonicalPourStatus maps timeout and card removal reasons', () => {
  assert.equal(resolveCanonicalPourStatus({ completion_reason: 'controller_timeout' }), 'timeout');
  assert.equal(resolveCanonicalPourStatus({ completion_reason: 'card_removed_close' }), 'card_removed');
});

test('resolveCanonicalPourStatus maps denied, non-sale and stopped outcomes', () => {
  assert.equal(resolveCanonicalPourStatus({ status: 'rejected' }), 'denied');
  assert.equal(resolveCanonicalPourStatus({ sale_kind: 'non_sale' }), 'non_sale');
  assert.equal(resolveCanonicalPourStatus({ status: 'zero_volume' }), 'stopped');
});

test('canonicalPourStatusLabel returns operator-facing copy', () => {
  assert.equal(canonicalPourStatusLabel('error'), 'Ошибка');
});
