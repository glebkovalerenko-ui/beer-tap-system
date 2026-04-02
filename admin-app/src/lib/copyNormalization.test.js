import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatSystemBlockedActionLabel,
  humanizeIncidentSource,
  humanizeIncidentType,
  normalizeSystemActionableStep,
  normalizeUserFacingBackendText,
} from './copyNormalization.js';

test('normalizeUserFacingBackendText translates tap runtime copy from backend', () => {
  assert.equal(normalizeUserFacingBackendText('Line is quiet and ready for the next operator action.'), 'Линия готова к следующему действию оператора.');
  assert.equal(normalizeUserFacingBackendText('Controller heartbeat stale'), 'Контроллер давно не выходил на связь');
  assert.equal(normalizeUserFacingBackendText('No heartbeat for 239 min'), 'Нет сигнала 239 мин');
  assert.equal(normalizeUserFacingBackendText('display assigned'), 'Экран подключён');
  assert.equal(normalizeUserFacingBackendText('reader ready'), 'Считыватель готов');
});

test('normalizeSystemActionableStep translates system next steps from backend', () => {
  assert.equal(
    normalizeSystemActionableStep('No blocked actions right now; continue regular shift workflow.'),
    'Сейчас блокировок нет: продолжайте работу смены в штатном режиме.',
  );
  assert.equal(
    normalizeSystemActionableStep('Review sync backlog: 3 pending items across 2 sessions.'),
    'Проверьте очередь синхронизации: 3 элементов в 2 визитах.',
  );
});

test('incident and system labels are humanized for active UI', () => {
  assert.equal(humanizeIncidentType('flow-closed-valve'), 'Поток при закрытом клапане');
  assert.equal(humanizeIncidentType('visit_force_unlock'), 'Принудительная разблокировка визита');
  assert.equal(humanizeIncidentSource('display_agent'), 'Экран');
  assert.equal(formatSystemBlockedActionLabel('incident_mutation'), 'Действия по инцидентам');
});
