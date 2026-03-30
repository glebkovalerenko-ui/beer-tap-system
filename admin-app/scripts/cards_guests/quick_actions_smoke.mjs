import { buildQuickActions } from '../../src/lib/cardsGuests/scenarios/quick_actions.js';

const enabled = buildQuickActions({
  lookup: { active_visit: { visit_id: 'v1' } },
  actionGuards: {
    topUp: { disabled: false, reason: '' },
    toggleBlock: { disabled: false, reason: '', isActive: true },
    reissue: { disabled: false, reason: '' },
    openHistory: { disabled: false, reason: '' },
    openVisit: { disabled: false, reason: '' },
  },
});
const denied = buildQuickActions({
  lookup: null,
  actionGuards: {
    topUp: { disabled: true, reason: 'Top-up unavailable.' },
    toggleBlock: { disabled: true, reason: 'Toggle unavailable.', isActive: false },
    reissue: { disabled: true, reason: 'Reissue unavailable.' },
    openHistory: { disabled: true, reason: 'History unavailable.' },
    openVisit: { disabled: true, reason: 'Visit unavailable.' },
  },
});

const checks = [
  { name: 'enabled topup action available', ok: enabled.find((item) => item.id === 'top-up')?.disabled === false },
  { name: 'denied topup action disabled', ok: denied.find((item) => item.id === 'top-up')?.disabled === true },
  { name: 'denied reissue action disabled', ok: denied.find((item) => item.id === 'reissue')?.disabled === true },
];

for (const check of checks) console.log(`[SMOKE][quick_actions] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
