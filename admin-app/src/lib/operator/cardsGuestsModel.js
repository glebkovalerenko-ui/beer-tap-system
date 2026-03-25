import { buildPhoneCandidates, buildQuickLookupResults, fullName, hasLookupTarget } from '../cardsGuests/scenarios/lookup.js';
import { buildQuickActions } from '../cardsGuests/scenarios/quick_actions.js';
import { buildRecentEvents } from '../cardsGuests/scenarios/recent_events.js';
import { formatRubAmount } from '../formatters.js';

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
    || (recentGuestPours[0]?.tap_id
      ? `Кран #${recentGuestPours[0].tap_id}`
      : (selectedVisit?.active_tap_id ? `Кран #${selectedVisit.active_tap_id}` : '—'));

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
  const lookupBalance = selectedGuest?.balance
    ?? selectedLookup?.guest?.balance
    ?? selectedLookup?.active_visit?.balance
    ?? null;
  const lookupVisitId = selectedVisit?.visit_id
    || selectedLookup?.active_visit?.visit_id
    || selectedLookup?.lost_card?.visit_id
    || null;
  const lookupSummaryItems = hasLookup
    ? [
      {
        key: 'card-state',
        label: 'Статус карты',
        value: selectedLookup?.is_lost
          ? 'Lost / нужна помощь'
          : selectedLookup?.active_visit
            ? 'Карта участвует в активной сессии'
            : selectedLookup?.guest
              ? 'Карта привязана к гостю'
              : selectedLookup?.card
                ? 'Карта есть, гость не найден'
                : 'Карта не найдена',
        tone: selectedLookup?.is_lost ? 'warning' : selectedLookup?.active_visit ? 'info' : 'neutral',
      },
      {
        key: 'balance',
        label: 'Баланс',
        value: lookupBalance != null ? formatRubAmount(lookupBalance) : '—',
        tone: lookupBalance != null && lookupBalance <= 0 ? 'warning' : 'neutral',
      },
      {
        key: 'active-visit',
        label: 'Активный визит',
        value: lookupVisitId ? `#${lookupVisitId}` : 'Нет активного визита',
        tone: lookupVisitId ? 'info' : 'neutral',
      },
      {
        key: 'last-tap',
        label: 'Последний кран',
        value: lastTapLabel || '—',
        tone: selectedVisit?.active_tap_id ? 'info' : 'neutral',
      },
      {
        key: 'recent-events',
        label: 'Последние события',
        value: recentEvents.length ? `${recentEvents.length} событий` : 'Нет событий',
        tone: recentEvents.length ? 'info' : 'neutral',
      },
    ]
    : [];

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
    lookupSummaryItems,
    quickActions,
  };
}
