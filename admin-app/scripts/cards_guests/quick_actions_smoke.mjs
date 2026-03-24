import { buildQuickActions } from '../../src/lib/cardsGuests/scenarios/quick_actions.js';

const enabled = buildQuickActions({
  lookup: { active_visit: { visit_id: 'v1' } },
  guest: { is_active: true },
  visit: { visit_id: 'v1' },
  canTopUp: true,
  canToggleBlock: true,
  canReissue: true,
  canOpenVisit: true,
  canViewHistory: true,
});
const denied = buildQuickActions({
  lookup: null,
  guest: null,
  visit: null,
  canTopUp: false,
  canToggleBlock: false,
  canReissue: false,
  canOpenVisit: false,
  canViewHistory: false,
});

const checks = [
  { name: 'enabled topup action available', ok: enabled.find((item) => item.id === 'top-up')?.disabled === false },
  { name: 'denied topup action disabled', ok: denied.find((item) => item.id === 'top-up')?.disabled === true },
  { name: 'denied reissue action disabled', ok: denied.find((item) => item.id === 'reissue')?.disabled === true },
];

for (const check of checks) console.log(`[SMOKE][quick_actions] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
