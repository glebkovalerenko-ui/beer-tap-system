export function getReissueTargetVisitId({ selectedVisit, selectedLookup }) {
  return selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id || null;
}

export function buildReissueHint(selectedLookup) {
  return selectedLookup?.is_lost
    ? 'Снимите lost при необходимости, затем считайте новую карту и завершите перевыпуск.'
    : 'Считайте новую карту и перенесите контекст активного визита на неё.';
}

export function validateReissueInput({ canReissue, selectedGuest, nextUid }) {
  if (!canReissue) {
    return { ok: false, reason: 'permission', message: 'Перевыпуск карты недоступен для текущей роли.' };
  }
  if (!selectedGuest) {
    return { ok: false, reason: 'guest', message: 'Невозможно перевыпустить карту без выбранного гостя.' };
  }
  if (!nextUid?.trim()) {
    return { ok: false, reason: 'uid', message: 'UID новой карты обязателен.' };
  }
  return { ok: true, reason: '', message: '' };
}
