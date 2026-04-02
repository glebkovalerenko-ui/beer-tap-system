import test from 'node:test';
import assert from 'node:assert/strict';

import { normalizeError } from './errorUtils.js';

test('normalizeError translates authentication failures for active UI flows', () => {
  assert.equal(normalizeError('Incorrect username or password'), 'Неверное имя пользователя или пароль');
  assert.equal(normalizeError(new Error('Could not validate credentials')), 'Требуется повторный вход в систему');
});

test('normalizeError translates common not-found backend details', () => {
  assert.equal(normalizeError({ detail: 'Guest not found' }), 'Гость не найден');
  assert.equal(normalizeError({ detail: 'Visit not found' }), 'Визит не найден');
  assert.equal(normalizeError({ detail: 'Card not found or not assigned to this guest' }), 'Карта не найдена или не привязана к этому гостю');
});

test('normalizeError translates lost-card workflow conflicts', () => {
  assert.equal(normalizeError({ detail: 'Only active visit can report lost card' }), 'Отметить потерю карты можно только у активного визита');
  assert.equal(
    normalizeError({
      detail: 'Cannot restore a lost card from the lost-cards queue while the related visit is still blocked; open the visit recovery flow and reissue, cancel lost, or service-close it first.',
    }),
    'Нельзя снять отметку потери из очереди потерянных карт, пока связанный визит заблокирован. Откройте раздел «Визиты» и выполните перевыпуск, снятие отметки потери или сервисное закрытие.'
  );
});

test('normalizeError translates raw validation details and nested payloads', () => {
  assert.equal(normalizeError({ detail: "Value must be 'true' or 'false'" }), "Значение должно быть 'true' или 'false'");
  assert.equal(normalizeError(JSON.stringify({ detail: 'Guest not found' })), 'Гость не найден');
});
