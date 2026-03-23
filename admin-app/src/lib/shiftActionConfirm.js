import { formatDateTimeRu } from './formatters.js';

export function formatShiftConfirmationTarget(shiftState, action) {
  if (action === 'close') {
    const shift = shiftState?.shift;
    if (!shift) {
      return 'Текущая открытая смена';
    }

    const shiftNumber = shift.id ? `№${shift.id}` : 'без номера';
    const openedAt = shift.opened_at ? `, открыта ${formatDateTimeRu(shift.opened_at)}` : '';
    return `текущая смена ${shiftNumber}${openedAt}`;
  }

  const shift = shiftState?.shift;
  if (shift?.closed_at) {
    const shiftNumber = shift.id ? `№${shift.id}` : 'без номера';
    const closedAt = shift.closed_at ? `, закрытой ${formatDateTimeRu(shift.closed_at)}` : '';
    return `новая текущая смена после смены ${shiftNumber}${closedAt}`;
  }

  return 'новая текущая смена';
}

export async function confirmShiftAction({ uiStore, shiftState, action }) {
  const target = formatShiftConfirmationTarget(shiftState, action);

  if (action === 'close') {
    return uiStore.confirm({
      title: 'Подтвердите закрытие смены',
      message: [
        `Будет немедленно запущено закрытие: ${target}.`,
        'После подтверждения операция сразу уйдёт в систему; отменить её из этого диалога или кнопкой назад нельзя.',
        'Закрывайте смену только если все операции по ней действительно завершены.'
      ].join('\n\n'),
      confirmText: 'Закрыть смену',
      cancelText: 'Не закрывать',
      danger: true,
    });
  }

  return uiStore.confirm({
    title: 'Открыть смену?',
    message: [
      `Будет открыта ${target}.`,
      'Пока вы не подтвердили действие, ничего не изменится.',
      'Если передумали, нажмите «Отмена» и открытие не выполнится.'
    ].join('\n\n'),
    confirmText: 'Открыть смену',
    cancelText: 'Отмена',
    danger: false,
  });
}
