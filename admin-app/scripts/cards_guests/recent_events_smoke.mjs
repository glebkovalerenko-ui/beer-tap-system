import { buildRecentEvents } from '../../src/lib/cardsGuests/scenarios/recent_events.js';

const guest = {
  transactions: [{ type: 'topup', amount: 500, created_at: '2026-03-24T12:00:00.000Z' }],
};
const visit = { visit_id: 'v1', opened_at: '2026-03-24T11:00:00.000Z' };
const lookup = { is_lost: true, lost_card: { reported_at: '2026-03-24T10:00:00.000Z' } };
const pours = [{ tap_id: 5, amount_charged: 120, poured_at: '2026-03-24T12:10:00.000Z' }];

const normal = buildRecentEvents({ guest, visit, lookup, pours });
const empty = buildRecentEvents({ guest: null, visit, lookup, pours });

const checks = [
  { name: 'recent events include pour event', ok: normal.some((item) => item.title.startsWith('Налив')) },
  { name: 'recent events sorted and non-empty', ok: normal.length > 0 },
  { name: 'recent events return empty without guest', ok: empty.length === 0 },
];

for (const check of checks) console.log(`[SMOKE][recent_events] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
