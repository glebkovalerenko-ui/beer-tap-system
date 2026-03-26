import test from 'node:test';
import assert from 'node:assert/strict';

import { getOperatorActionDescriptor } from './actionDescriptors.js';

test('getOperatorActionDescriptor adapts guest block copy to active state', () => {
  const descriptor = getOperatorActionDescriptor('card.toggle_block', {
    guestName: 'Alex Stone',
    isActive: true,
  });

  assert.match(descriptor.title, /Заблокировать гостя/);
  assert.match(descriptor.description, /Alex Stone/);
  assert.equal(descriptor.danger, true);
});

test('getOperatorActionDescriptor exposes reconcile fields and validation', () => {
  const descriptor = getOperatorActionDescriptor('session.reconcile', {
    visitId: 'v-10',
    defaultTapId: 14,
  });

  assert.equal(descriptor.fields[0]?.initialValue, 14);
  assert.deepEqual(descriptor.validate({
    shortId: 'bad',
    amount: '-1',
  }), {
    shortId: 'Используйте 6-8 букв или цифр.',
    amount: 'Введите корректную сумму.',
  });
});
