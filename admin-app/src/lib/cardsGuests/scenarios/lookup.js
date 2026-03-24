import { formatRubAmount } from '../../formatters.js';

export const fullName = (guest) => [guest?.last_name, guest?.first_name, guest?.patronymic].filter(Boolean).join(' ');

export function buildPhoneCandidates(guests, query, limit = 12) {
  const q = query?.trim().toLowerCase();
  if (!q) return [];
  return (guests || []).filter((guest) => [
    guest.phone_number,
    guest.id_document,
    guest.guest_id,
    fullName(guest),
    ...(guest.cards || []).map((card) => card.card_uid),
  ].filter(Boolean).some((value) => String(value).toLowerCase().includes(q))).slice(0, limit);
}

export function buildQuickLookupResults(phoneCandidates, activeVisits) {
  return (phoneCandidates || []).map((guest) => ({
    guest_id: guest.guest_id,
    label: fullName(guest),
    meta: [guest.phone_number, guest.id_document].filter(Boolean).join(' · ') || 'Без контактов',
    trailing: (activeVisits || []).some((visit) => visit.guest_id === guest.guest_id) ? 'Активный визит' : formatRubAmount(guest.balance),
  }));
}

export function resolveLookupScenario(selectedLookup, canReissue) {
  return selectedLookup?.is_lost && canReissue ? 'reissue' : 'check-card';
}

export function hasLookupTarget(selectedLookup) {
  return Boolean(
    selectedLookup?.guest?.guest_id
    || selectedLookup?.active_visit?.visit_id
    || selectedLookup?.lost_card?.visit_id
    || selectedLookup?.card_uid
    || selectedLookup?.card?.uid
  );
}
