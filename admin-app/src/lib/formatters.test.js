import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTapGuestDisplaySnapshot, formatPriceDisplayMode } from './formatters.js';

test('formatPriceDisplayMode returns Russian labels for visible price modes', () => {
  assert.equal(formatPriceDisplayMode('per_100ml'), '₽ / 100 мл');
  assert.equal(formatPriceDisplayMode('per_liter'), '₽ / л');
  assert.equal(formatPriceDisplayMode('auto'), 'Авто');
  assert.equal(formatPriceDisplayMode('', 'По напитку'), 'По напитку');
});

test('buildTapGuestDisplaySnapshot uses Russian scenario labels for empty tap screen', () => {
  const snapshot = buildTapGuestDisplaySnapshot(
    {
      display_enabled: true,
      operations: {
        productState: 'no_keg',
        displayStatus: { label: 'Экран на связи', state: 'ok' },
      },
      keg: null,
    },
    { enabled: true },
  );

  assert.equal(snapshot.scenario, 'fallback_empty');
  assert.equal(snapshot.scenarioLabel, 'Гость видит экран пустого крана');
});
