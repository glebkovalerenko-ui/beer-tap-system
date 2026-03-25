import { buildPhoneCandidates, buildQuickLookupResults, fullName, hasLookupTarget } from '../cardsGuests/scenarios/lookup.js';
import { buildQuickActions } from '../cardsGuests/scenarios/quick_actions.js';
import { buildRecentEvents } from '../cardsGuests/scenarios/recent_events.js';

export const SCENARIO_ACTION_HANDLERS = {
  'top-up': 'open-top-up',
  'open-visit': 'open-visit',
  'open-history': 'open-history',
  'toggle-block': 'toggle-block',
  reissue: 'reissue',
};

export function resolveScenarioActionHandler(actionId) {
  return SCENARIO_ACTION_HANDLERS[actionId] || 'none';
}

export function buildCardsGuestsViewModel({
  guests,
  activeVisits,
  pours,
  phoneQuery,
  selectedGuestId,
  selectedLookup,
  permissions,
}) {
  const safeGuests = guests || [];
  const safeVisits = activeVisits || [];
  const safePours = pours || [];
  const canTopUp = Boolean(permissions?.canTopUp);
  const canToggleBlock = Boolean(permissions?.canToggleBlock);
  const canReissue = Boolean(permissions?.canReissue);
  const canOpenVisit = Boolean(permissions?.canOpenVisit);
  const canViewHistory = Boolean(permissions?.canViewHistory);

  const phoneCandidates = buildPhoneCandidates(safeGuests, phoneQuery || '');
  const quickLookupResults = buildQuickLookupResults(phoneCandidates, safeVisits);

  let selectedGuest = selectedGuestId
    ? safeGuests.find((guest) => guest.guest_id === selectedGuestId) || null
    : null;

  if (!selectedGuest && selectedLookup?.guest?.guest_id) {
    selectedGuest = safeGuests.find((guest) => guest.guest_id === selectedLookup.guest.guest_id) || null;
  }

  const selectedVisit = selectedGuest
    ? safeVisits.find((visit) => visit.guest_id === selectedGuest.guest_id) || null
    : null;

  const recentGuestPours = selectedGuest
    ? safePours.filter((item) => item?.guest?.guest_id === selectedGuest.guest_id).slice(0, 6)
    : [];

  const lastTapLabel = recentGuestPours[0]?.tap?.display_name
    || (recentGuestPours[0]?.tap_id ? `Кран #${recentGuestPours[0].tap_id}` : '—');

  const recentEvents = buildRecentEvents({
    guest: selectedGuest,
    visit: selectedVisit,
    lookup: selectedLookup,
    pours: recentGuestPours,
  });

  const lookupGuestName = selectedGuest
    ? fullName(selectedGuest)
    : (selectedLookup?.guest?.full_name || 'Гость не определён');

  const hasLookup = hasLookupTarget(selectedLookup);
  const quickActions = buildQuickActions({
    lookup: selectedLookup,
    guest: selectedGuest,
    visit: selectedVisit,
    canTopUp,
    canToggleBlock,
    canReissue,
    canOpenVisit,
    canViewHistory,
  });

  return {
    phoneCandidates,
    quickLookupResults,
    selectedGuest,
    selectedVisit,
    recentGuestPours,
    lastTapLabel,
    recentEvents,
    lookupGuestName,
    hasLookup,
    quickActions,
  };
}
