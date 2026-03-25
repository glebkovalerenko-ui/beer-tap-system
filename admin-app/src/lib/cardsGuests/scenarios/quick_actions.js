import { createQuickActionDescriptor, orderQuickActionDescriptors } from '../../operator/quickActionDescriptors.js';

export function buildQuickActions({ lookup, guest, visit, canTopUp, canToggleBlock, canReissue, canOpenVisit, canViewHistory }) {
  return orderQuickActionDescriptors([
    createQuickActionDescriptor({
      id: 'top-up',
      title: 'Пополнить',
      description: canTopUp
        ? 'Быстро пополнить баланс после проверки карты и гостя.'
        : 'Недоступно без права пополнения баланса.',
      disabled: !guest || !canTopUp,
    }),
    createQuickActionDescriptor({
      id: 'toggle-block',
      title: guest?.is_active ? 'Заблокировать' : 'Разблокировать',
      description: canToggleBlock
        ? 'Изменить статус гостя, если этого требует ситуация смены.'
        : 'Недоступно без права блокировки карты или гостя.',
      disabled: !guest || !canToggleBlock,
    }),
    createQuickActionDescriptor({
      id: 'reissue',
      title: lookup?.is_lost ? 'Снять lost / перевыпустить' : 'Пометить lost / перевыпустить',
      description: canReissue
        ? 'Отметить карту как lost, снять lost или перевыпустить её в рабочем сценарии.'
        : 'Недоступно без права работы с lost-картами.',
      disabled: !canReissue || !(guest && (lookup?.is_lost || visit?.visit_id || lookup?.active_visit?.visit_id)),
      tone: lookup?.is_lost ? 'danger' : 'neutral',
    }),
    createQuickActionDescriptor({
      id: 'open-history',
      title: 'История',
      description: canViewHistory
        ? 'Открыть историю по карте или гостю, чтобы быстро объяснить событие.'
        : 'Недоступно без права просмотра истории.',
      disabled: !lookup || !canViewHistory,
    }),
    createQuickActionDescriptor({
      id: 'open-visit',
      title: 'Активная сессия',
      description: canOpenVisit
        ? 'Перейти в действующий визит и продолжить обслуживание без повторного поиска.'
        : 'Недоступно без права перехода в активную сессию.',
      disabled: !canOpenVisit || !(visit?.visit_id || lookup?.active_visit?.visit_id || lookup?.lost_card?.visit_id),
    }),
  ], ['top-up', 'toggle-block', 'reissue', 'open-history', 'open-visit']);
}
