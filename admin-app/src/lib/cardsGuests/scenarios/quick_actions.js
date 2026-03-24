export function buildQuickActions({ lookup, guest, visit, canTopUp, canToggleBlock, canReissue, canOpenVisit, canViewHistory }) {
  return [
    {
      id: 'check-card',
      title: 'Проверить карту',
      description: 'Быстрый операторский summary: статус, баланс, визит, кран и события.',
      disabled: !lookup,
    },
    {
      id: 'top-up',
      title: 'Пополнить баланс',
      description: canTopUp ? 'Операторское действие после успешной идентификации гостя.' : 'Недоступно без права cards_top_up.',
      disabled: !guest || !canTopUp,
    },
    {
      id: 'toggle-block',
      title: guest?.is_active ? 'Заблокировать' : 'Разблокировать',
      description: canToggleBlock ? 'Management-действие вынесено из lookup-summary, но запускается отсюда.' : 'Недоступно без права cards_block_manage.',
      disabled: !guest || !canToggleBlock,
    },
    {
      id: 'reissue',
      title: lookup?.is_lost ? 'Перевыпустить lost-карту' : 'Lost / перевыпуск',
      description: canReissue ? 'Management-сценарий перевыпуска после проверки статуса карты.' : 'Недоступно без права cards_reissue_manage.',
      disabled: !canReissue || !(guest && (lookup?.is_lost || visit?.visit_id || lookup?.active_visit?.visit_id)),
      tone: lookup?.is_lost ? 'danger' : 'muted',
    },
    {
      id: 'open-visit',
      title: 'Открыть активную сессию',
      description: canOpenVisit ? 'Перейти в действующий визит прямо из lookup-flow.' : 'Недоступно без права перехода в активную сессию.',
      disabled: !canOpenVisit || !(visit?.visit_id || lookup?.active_visit?.visit_id || lookup?.lost_card?.visit_id),
    },
    {
      id: 'open-history',
      title: 'Открыть историю',
      description: canViewHistory ? 'Посмотреть историю по текущей карте или гостю.' : 'Недоступно без права cards_history_view.',
      disabled: !lookup || !canViewHistory,
    },
  ];
}
