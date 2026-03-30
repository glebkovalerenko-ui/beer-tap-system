import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildOperatorPourPresentation,
  formatPourCompletionReason,
  formatPourSyncState,
  presentPourLifecycle,
} from './pourPresentation.js';

test('formatPourSyncState hides raw sync codes behind operator labels', () => {
  assert.equal(formatPourSyncState('accounted').label, 'Учтён системой');
  assert.equal(formatPourSyncState('pending_sync').label, 'Ждёт синхронизации');
});

test('formatPourCompletionReason maps internal stop reasons to operator language', () => {
  assert.equal(
    formatPourCompletionReason('flow_detected_when_valve_closed_without_active_session').label,
    'Поток зафиксирован без открытого визита',
  );
  assert.equal(
    formatPourCompletionReason('no_card_no_session').label,
    'Карта не считана, визит не открыт',
  );
});

test('presentPourLifecycle keeps technical codes secondary for non-sale flow lifecycle', () => {
  const lifecycle = presentPourLifecycle({
    summary: {
      source_kind: 'flow',
      sync_state: 'accounted',
    },
    lifecycle: [
      { key: 'reader', value: 'no' },
      { key: 'start', value: 'no_card_no_session' },
      { key: 'sync', value: 'accounted' },
    ],
  });

  assert.deepEqual(
    lifecycle.map((item) => [item.operatorLabel, item.operatorValue]),
    [
      ['Карта у считывателя', 'Нет'],
      ['Налив начался', 'Карта не считана, визит не открыт'],
      ['Учёт и синхронизация', 'Учтён системой'],
    ],
  );
});

test('buildOperatorPourPresentation returns summary labels ready for first-layer UI', () => {
  const presentation = buildOperatorPourPresentation({
    summary: {
      sync_state: 'rejected',
      completion_reason: 'controller_timeout',
    },
    lifecycle: [],
  });

  assert.equal(presentation.sync.label, 'Нужна проверка синхронизации');
  assert.equal(presentation.completion.label, 'Остановлен по таймауту контроллера');
});
