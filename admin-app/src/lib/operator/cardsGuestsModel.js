import { buildPhoneCandidates, buildQuickLookupResults, fullName, hasLookupTarget } from '../cardsGuests/scenarios/lookup.js';
import { buildQuickActions } from '../cardsGuests/scenarios/quick_actions.js';
import { buildRecentEvents } from '../cardsGuests/scenarios/recent_events.js';
import { formatRubAmount } from '../formatters.js';
import { normalizeOperatorActionPolicy } from './actionPolicyAdapter.js';

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

function toGuard(policy, fallback, meta = {}) {
  const normalized = normalizeOperatorActionPolicy(policy || {
    allowed: fallback.allowed,
    confirm_required: fallback.confirmRequired,
    reason_code_required: fallback.reasonCodeRequired,
    disabled_reason: fallback.reason,
  });

  return {
    ...meta,
    ...normalized,
    disabled: !normalized.allowed,
    reason: normalized.disabledReason || '',
  };
}

function buildActionGuards({ lookup, guest, visit, permissions }) {
  const policies = lookup?.action_policies || {};
  const visitId = visit?.visit_id || lookup?.active_visit?.visit_id || lookup?.lost_card?.visit_id || null;
  const isGuestActive = Boolean(guest?.is_active ?? lookup?.guest?.is_active);

  return {
    topUp: toGuard(policies.top_up, {
      allowed: Boolean(guest) && Boolean(permissions?.canTopUp),
      reason: 'Guest context and top-up permission are required.',
    }),
    toggleBlock: toGuard(policies.toggle_block, {
      allowed: Boolean(guest) && Boolean(permissions?.canToggleBlock),
      confirmRequired: true,
      reason: 'Guest context and block permission are required.',
    }, {
      isActive: isGuestActive,
    }),
    markLost: toGuard(policies.mark_lost, {
      allowed: Boolean(permissions?.canReissue) && Boolean(visitId) && !lookup?.is_lost,
      confirmRequired: true,
      reason: lookup?.is_lost
        ? 'Card is already marked as lost.'
        : 'An active visit is required before the card can be marked as lost.',
    }),
    restoreLost: toGuard(policies.restore_lost, {
      allowed: Boolean(permissions?.canReissue) && Boolean(lookup?.is_lost),
      confirmRequired: true,
      reason: 'Card is not currently marked as lost.',
    }),
    reissue: toGuard(policies.reissue, {
      allowed: Boolean(permissions?.canReissue) && Boolean(guest) && Boolean(lookup?.is_lost || visitId),
      reason: 'Guest context with an active or lost card workflow is required.',
    }),
    openHistory: toGuard(policies.open_history, {
      allowed: Boolean(permissions?.canViewHistory) && Boolean(lookup),
      reason: 'A resolved card is required to open history.',
    }),
    openVisit: toGuard(policies.open_visit, {
      allowed: Boolean(permissions?.canOpenVisit) && Boolean(visitId),
      reason: 'There is no active visit linked to this card.',
    }),
  };
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

  const lastTapLabel = selectedLookup?.last_tap_label
    || recentGuestPours[0]?.tap?.display_name
    || (recentGuestPours[0]?.tap_id
      ? `Кран #${recentGuestPours[0].tap_id}`
      : (selectedVisit?.active_tap_id ? `Кран #${selectedVisit.active_tap_id}` : '—'));

  const recentEvents = Array.isArray(selectedLookup?.recent_events) && selectedLookup.recent_events.length > 0
    ? selectedLookup.recent_events
    : buildRecentEvents({
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
    ?? (selectedLookup?.guest?.balance_cents != null ? selectedLookup.guest.balance_cents / 100 : null)
    ?? selectedLookup?.active_visit?.balance
    ?? null;
  const lookupVisitId = selectedVisit?.visit_id
    || selectedLookup?.active_visit?.visit_id
    || selectedLookup?.lost_card?.visit_id
    || null;
  const lookupSummaryItems = hasLookup
    ? (Array.isArray(selectedLookup?.lookup_summary_items) && selectedLookup.lookup_summary_items.length > 0
      ? selectedLookup.lookup_summary_items
      : [
        {
          key: 'card-state',
          label: 'Статус карты',
          value: {
            active_visit: 'Карта назначена активному визиту',
            active_blocked_lost_card: 'Визит заблокирован: карта потеряна',
            available_pool_card: 'Карта доступна в пуле',
            returned_to_pool_card: 'Карта возвращена в пул',
            lost_card: 'Карта потеряна',
            retired_card: 'Карта выведена из эксплуатации',
            unknown_card: 'Карта не найдена',
          }[selectedLookup?.lookup_outcome] || 'Статус карты уточняется',
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
      ])
    : [];

  const actionGuards = buildActionGuards({
    lookup: selectedLookup,
    guest: selectedGuest,
    visit: selectedVisit,
    permissions,
  });

  const quickActions = buildQuickActions({
    lookup: selectedLookup,
    actionGuards,
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
    actionGuards,
  };
}
