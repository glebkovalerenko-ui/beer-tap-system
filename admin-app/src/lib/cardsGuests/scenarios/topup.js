export function resolveTopUpPreconditions({ canTopUp, hasGuest, isShiftOpen }) {
  if (!canTopUp) {
    return { ok: false, reason: 'permission', message: 'Пополнение баланса недоступно для текущей роли.' };
  }
  if (!hasGuest) {
    return { ok: false, reason: 'guest', message: 'Сначала выберите гостя через lookup.' };
  }
  if (!isShiftOpen) {
    return { ok: false, reason: 'shift', message: 'Сначала откройте смену на дашборде, затем выполните пополнение.' };
  }
  return { ok: true, reason: '', message: '' };
}
