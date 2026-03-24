import { resolveTopUpPreconditions } from '../../src/lib/cardsGuests/scenarios/topup.js';

const valid = resolveTopUpPreconditions({ canTopUp: true, hasGuest: true, isShiftOpen: true });
const noPermission = resolveTopUpPreconditions({ canTopUp: false, hasGuest: true, isShiftOpen: true });
const noShift = resolveTopUpPreconditions({ canTopUp: true, hasGuest: true, isShiftOpen: false });

const checks = [
  { name: 'valid topup preconditions pass', ok: valid.ok === true },
  { name: 'permission branch returns error', ok: noPermission.ok === false && noPermission.reason === 'permission' },
  { name: 'shift branch returns error', ok: noShift.ok === false && noShift.reason === 'shift' },
];

for (const check of checks) console.log(`[SMOKE][topup] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
