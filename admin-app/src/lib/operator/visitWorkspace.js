function normalizeText(value) {
  return String(value || '').trim().toLowerCase();
}

export function visitLauncherGuestName(guest) {
  return [
    guest?.last_name,
    guest?.first_name,
    guest?.patronymic,
  ].filter(Boolean).join(' ') || 'Гость без имени';
}

export function buildVisitLauncherCandidates({ guests = [], activeVisits = [], query = '', limit = 6 } = {}) {
  const normalizedQuery = normalizeText(query);
  if (normalizedQuery.length < 2) {
    return [];
  }

  const activeByGuestId = new Map(
    (activeVisits || []).map((visit) => [String(visit?.guest_id || ''), visit]),
  );

  return (guests || [])
    .filter((guest) => {
      const fields = [
        visitLauncherGuestName(guest),
        guest?.phone_number,
        ...(Array.isArray(guest?.cards) ? guest.cards.map((card) => card?.card_uid) : []),
      ];
      return fields.some((value) => normalizeText(value).includes(normalizedQuery));
    })
    .map((guest) => {
      const activeVisit = activeByGuestId.get(String(guest?.guest_id || '')) || null;
      const cardUid = guest?.cards?.[0]?.card_uid || '';
      return {
        guestId: guest?.guest_id || '',
        fullName: visitLauncherGuestName(guest),
        phoneNumber: guest?.phone_number || '',
        balance: guest?.balance ?? 0,
        cardUid,
        activeVisitId: activeVisit?.visit_id || '',
        activeTapId: activeVisit?.active_tap_id || null,
        actionLabel: activeVisit?.visit_id ? 'Продолжить визит' : 'Открыть визит',
      };
    })
    .sort((left, right) => {
      if (Boolean(left.activeVisitId) !== Boolean(right.activeVisitId)) {
        return left.activeVisitId ? -1 : 1;
      }
      return left.fullName.localeCompare(right.fullName, 'ru');
    })
    .slice(0, limit);
}

export function resolveVisitFocusTarget(items = [], focusVisitId = '') {
  const targetId = String(focusVisitId || '').trim();
  if (!targetId) {
    return null;
  }
  return items.find((item) => String(item?.visit_id || '') === targetId) || null;
}
