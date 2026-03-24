import { buildReissueHint, getReissueTargetVisitId, validateReissueInput } from '../../src/lib/cardsGuests/scenarios/lost_reissue.js';

const valid = validateReissueInput({ canReissue: true, selectedGuest: { guest_id: 'g1' }, nextUid: 'NEW1' });
const missingUid = validateReissueInput({ canReissue: true, selectedGuest: { guest_id: 'g1' }, nextUid: ' ' });
const missingPermission = validateReissueInput({ canReissue: false, selectedGuest: { guest_id: 'g1' }, nextUid: 'NEW1' });

const checks = [
  { name: 'valid reissue input passes', ok: valid.ok === true },
  { name: 'missing uid fails', ok: missingUid.ok === false && missingUid.reason === 'uid' },
  { name: 'permission fails', ok: missingPermission.ok === false && missingPermission.reason === 'permission' },
  { name: 'target visit derived from active visit', ok: getReissueTargetVisitId({ selectedVisit: null, selectedLookup: { active_visit: { visit_id: 'v1' } } }) === 'v1' },
  { name: 'lost hint generated', ok: buildReissueHint({ is_lost: true }).includes('lost') },
];

for (const check of checks) console.log(`[SMOKE][lost_reissue] ${check.ok ? 'OK' : 'FAIL'}: ${check.name}`);
if (checks.some((check) => !check.ok)) process.exit(1);
