import { createQuickActionDescriptor, orderQuickActionDescriptors } from '../../operator/quickActionDescriptors.js';

function withReason(descriptor, reason) {
  return {
    ...descriptor,
    reason,
  };
}

export function buildQuickActions({ lookup, actionGuards }) {
  const guards = actionGuards || {};

  return orderQuickActionDescriptors([
    withReason(createQuickActionDescriptor({
      id: 'top-up',
      title: 'Пополнить',
      description: guards.topUp?.disabled
        ? (guards.topUp.reason || 'Пополнение сейчас недоступно.')
        : 'Быстро пополнить баланс после проверки карты и гостя.',
      disabled: Boolean(guards.topUp?.disabled),
    }), guards.topUp?.reason),
    withReason(createQuickActionDescriptor({
      id: 'toggle-block',
      title: guards.toggleBlock?.isActive ? 'Заблокировать' : 'Разблокировать',
      description: guards.toggleBlock?.disabled
        ? (guards.toggleBlock.reason || 'Изменение статуса гостя сейчас недоступно.')
        : 'Изменить статус гостя без выхода из рабочего сценария.',
      disabled: Boolean(guards.toggleBlock?.disabled),
    }), guards.toggleBlock?.reason),
    withReason(createQuickActionDescriptor({
      id: 'reissue',
      title: lookup?.is_lost ? 'Восстановить / перевыпустить' : 'Потеря / перевыпуск',
      description: guards.reissue?.disabled
        ? (guards.reissue.reason || 'Сценарий перевыпуска сейчас недоступен.')
        : 'Продолжить сценарий потерянной карты или перевыпуска без выхода из контекста.',
      disabled: Boolean(guards.reissue?.disabled),
      tone: lookup?.is_lost ? 'danger' : 'neutral',
    }), guards.reissue?.reason),
    withReason(createQuickActionDescriptor({
      id: 'open-history',
      title: 'История',
      description: guards.openHistory?.disabled
        ? (guards.openHistory.reason || 'История сейчас недоступна.')
        : 'Открыть историю карты и гостя, чтобы объяснить последнее событие.',
      disabled: Boolean(guards.openHistory?.disabled),
    }), guards.openHistory?.reason),
    withReason(createQuickActionDescriptor({
      id: 'open-visit',
      title: 'Активный визит',
      description: guards.openVisit?.disabled
        ? (guards.openVisit.reason || 'Активный визит сейчас недоступен.')
        : 'Сразу открыть активный визит, связанный с этой картой.',
      disabled: Boolean(guards.openVisit?.disabled),
    }), guards.openVisit?.reason),
  ], ['top-up', 'toggle-block', 'reissue', 'open-history', 'open-visit']);
}
