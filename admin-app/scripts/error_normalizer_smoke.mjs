import { logError, normalizeError } from '../src/lib/errorUtils.js';

const scenarios = [
  {
    name: '404 missing resource',
    error: { status: 404, endpoint: '/api/shifts/00000000-0000-0000-0000-000000000000/reports/x' },
  },
  {
    name: '409 conflict detail object',
    error: { status: 409, endpoint: '/api/shifts/close', detail: { reason: 'active_visits_exist' } },
  },
  {
    name: '500 empty payload',
    error: { status: 500, endpoint: '/api/sync/pours', message: '' },
  },
];

let hasEmpty = false;

for (const scenario of scenarios) {
  const normalized = normalizeError(scenario.error);
  logError(`smoke.${scenario.name}`, scenario.error);
  console.log(`[SMOKE] ${scenario.name}: ${normalized}`);
  if (!normalized || normalized.trim().length === 0) {
    hasEmpty = true;
  }
}

if (hasEmpty) {
  console.error('[SMOKE] Empty normalized message detected.');
  process.exit(1);
}

console.log('[SMOKE] All error messages are non-empty.');
