import { buildPhoneCandidates, buildQuickLookupResults, hasLookupTarget, resolveLookupScenario } from '../../src/lib/cardsGuests/scenarios/lookup.js';

const guests = [{ guest_id: 'g1', first_name: 'Иван', last_name: 'Иванов', phone_number: '+79990000001', balance: 300, cards: [{ card_uid: 'ABC123' }] }];
const visits = [{ visit_id: 'v1', guest_id: 'g1' }];

const matched = buildPhoneCandidates(guests, 'abc');
const empty = buildPhoneCandidates(guests, '');
const results = buildQuickLookupResults(matched, visits);

const checks = [
  { name: 'lookup finds guest by card uid', ok: matched.length === 1 && matched[0].guest_id === 'g1' },
  { name: 'lookup returns empty list on empty query', ok: empty.length === 0 },
  { name: 'quick results mark active visit', ok: results[0]?.trailing === 'Активный визит' },
  { name: 'scenario switches to reissue for lost card', ok: resolveLookupScenario({ is_lost: true }, true) === 'reissue' },
  { name: 'hasLookupTarget detects unresolved payload as false', ok: hasLookupTarget({}) === false },
];

for (const check of checks) console.log(`[SMOKE][lookup] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
