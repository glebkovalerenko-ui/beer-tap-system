function tapName(context = {}) {
  return context.tap?.display_name || context.tapName || 'этот кран';
}

function sessionName(context = {}) {
  return context.sessionLabel || (context.visitId ? `визит #${context.visitId}` : 'этот визит');
}

function guestName(context = {}) {
  return context.guestName || 'этот гость';
}

function incidentName(context = {}) {
  return context.incidentId ? `инцидент #${context.incidentId}` : 'этот инцидент';
}

const OPERATOR_ACTION_DESCRIPTORS = {
  'session.close': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Закрыть визит',
    description: `Закройте ${sessionName(context)} и сразу обновите его в журнале визитов.`,
    submitText: 'Закрыть визит',
    successMessage: 'Визит закрыт.',
    danger: true,
    defaultReasonCode: 'incident-response',
  }),
  'session.force_unlock': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Снять блокировку с визита',
    description: `Снимите блокировку с ${sessionName(context)} и зафиксируйте вмешательство оператора.`,
    submitText: 'Снять блокировку',
    successMessage: 'Блокировка снята.',
    defaultReasonCode: 'hardware-fault',
  }),
  'session.mark_lost_card': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Пометить карту как потерянную',
    description: `Переведите ${sessionName(context)} в сценарий потерянной карты, чтобы безопасно продолжить перевыпуск или восстановление.`,
    submitText: 'Пометить как потерянную',
    successMessage: 'Карта помечена как потерянная.',
    danger: true,
    defaultReasonCode: 'security',
  }),
  'session.reconcile': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Ручная сверка налива',
    description: `Зафиксируйте ручную сверку для ${sessionName(context)}.`,
    submitText: 'Сохранить сверку',
    successMessage: 'Ручная сверка сохранена.',
    defaultReasonCode: 'incident-response',
    fields: [
      {
        name: 'tapId',
        label: 'Кран',
        type: 'number',
        required: true,
        min: 1,
        step: 1,
        initialValue: context.defaultTapId ?? '',
      },
      {
        name: 'shortId',
        label: 'Короткий ID',
        type: 'text',
        required: true,
        placeholder: '6-8 символов',
        initialValue: '',
      },
      {
        name: 'volumeMl',
        label: 'Объём, мл',
        type: 'number',
        required: true,
        min: 1,
        step: 1,
        initialValue: '250',
      },
      {
        name: 'amount',
        label: 'Сумма',
        type: 'text',
        required: true,
        placeholder: '175.00',
        inputMode: 'decimal',
        initialValue: '175.00',
      },
    ],
    validate(values = {}) {
      const errors = {};
      if (!/^[A-Za-z0-9_-]{6,8}$/.test(String(values.shortId || '').trim())) {
        errors.shortId = 'Используйте 6-8 букв или цифр.';
      }
      const amount = Number(values.amount);
      if (!Number.isFinite(amount) || amount < 0) {
        errors.amount = 'Введите корректную сумму.';
      }
      return errors;
    },
  }),
  'tap.stop': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Остановить налив и заблокировать кран',
    description: `Остановите текущий налив на ${tapName(context)} и переведите кран в заблокированное состояние.`,
    submitText: 'Остановить налив',
    successMessage: 'Статус крана обновлён.',
    danger: true,
    defaultReasonCode: 'safety',
  }),
  'tap.lock': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Заблокировать кран',
    description: `Заблокируйте ${tapName(context)} до устранения проблемы.`,
    submitText: 'Заблокировать кран',
    successMessage: 'Статус крана обновлён.',
  }),
  'tap.unlock': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Разблокировать кран',
    description: `Верните ${tapName(context)} в рабочее состояние.`,
    submitText: 'Разблокировать кран',
    successMessage: 'Статус крана обновлён.',
  }),
  'tap.cleaning': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Перевести кран в промывку',
    description: `Переведите ${tapName(context)} в режим промывки.`,
    submitText: 'Начать промывку',
    successMessage: 'Статус крана обновлён.',
  }),
  'tap.mark_ready': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Вернуть кран в готовность',
    description: `Верните ${tapName(context)} в статус «Готов» после обслуживания.`,
    submitText: 'Вернуть в готовность',
    successMessage: 'Статус крана обновлён.',
  }),
  'card.toggle_block': (context = {}) => ({
    mode: 'confirm-only',
    title: context.isActive ? 'Заблокировать гостя' : 'Разблокировать гостя',
    description: context.isActive
      ? `Ограничьте ${guestName(context)} в операторском потоке до завершения проверки.`
      : `Верните ${guestName(context)} в активный статус.`,
    submitText: context.isActive ? 'Заблокировать гостя' : 'Разблокировать гостя',
    successMessage: context.isActive ? 'Гость заблокирован.' : 'Гость разблокирован.',
    danger: Boolean(context.isActive),
  }),
  'card.mark_lost': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Пометить карту как потерянную',
    description: `Переведите ${guestName(context)} в сценарий потерянной карты, чтобы безопасно продолжить визит через перевыпуск.`,
    submitText: 'Пометить карту',
    successMessage: 'Карта помечена как потерянная.',
    danger: true,
  }),
  'card.restore_lost': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Снять отметку потери',
    description: `Снимите отметку потери у ${guestName(context)} и верните карту в обычный рабочий сценарий.`,
    submitText: 'Снять отметку',
    successMessage: 'Отметка потери снята.',
  }),
  'incident.claim': (context = {}) => ({
    mode: 'incident-form',
    title: 'Взять инцидент в работу',
    description: `Назначьте ответственного и зафиксируйте первый шаг по ${incidentName(context)}.`,
    submitText: 'Сохранить действие',
    successMessage: 'Действие по инциденту сохранено.',
    fields: [
      {
        name: 'owner',
        label: 'Ответственный',
        type: 'text',
        required: true,
        placeholder: 'Оператор или старший смены',
        initialValue: context.owner || '',
      },
      {
        name: 'note',
        label: 'Первый шаг',
        type: 'textarea',
        rows: 5,
        placeholder: 'Что уже проверили?',
        initialValue: context.note || '',
      },
    ],
  }),
  'incident.note': (context = {}) => ({
    mode: 'incident-form',
    title: 'Добавить заметку по инциденту',
    description: `Зафиксируйте последнее наблюдение оператора по ${incidentName(context)}.`,
    submitText: 'Сохранить действие',
    successMessage: 'Действие по инциденту сохранено.',
    fields: [
      {
        name: 'note',
        label: 'Заметка оператора',
        type: 'textarea',
        rows: 5,
        required: true,
        placeholder: 'Что изменилось и что должен знать следующий сотрудник?',
        initialValue: context.note || '',
      },
    ],
  }),
  'incident.escalate': (context = {}) => ({
    mode: 'incident-form',
    title: 'Эскалировать инцидент',
    description: `Опишите, что уже проверили и почему ${incidentName(context)} нужно передать дальше.`,
    submitText: 'Сохранить действие',
    successMessage: 'Действие по инциденту сохранено.',
    fields: [
      {
        name: 'note',
        label: 'Что уже проверили',
        type: 'textarea',
        rows: 4,
        placeholder: 'Какие проверки уже выполнены на смене.',
        initialValue: context.note || '',
      },
      {
        name: 'escalationReason',
        label: 'Причина эскалации',
        type: 'textarea',
        rows: 4,
        required: true,
        placeholder: 'Почему нужен следующий уровень разбора?',
        initialValue: context.escalationReason || '',
      },
    ],
  }),
  'incident.close': (context = {}) => ({
    mode: 'incident-form',
    title: 'Закрыть инцидент',
    description: `Зафиксируйте итог решения по ${incidentName(context)}.`,
    submitText: 'Сохранить действие',
    successMessage: 'Действие по инциденту сохранено.',
    fields: [
      {
        name: 'note',
        label: 'Что сделали',
        type: 'textarea',
        rows: 4,
        placeholder: 'Какие шаги выполнили перед закрытием.',
        initialValue: context.note || '',
      },
      {
        name: 'resolutionSummary',
        label: 'Итог решения',
        type: 'textarea',
        rows: 4,
        required: true,
        placeholder: 'Почему инцидент можно считать закрытым?',
        initialValue: context.resolutionSummary || '',
      },
    ],
  }),
};

export function getOperatorActionDescriptor(actionKey, context = {}) {
  const factory = OPERATOR_ACTION_DESCRIPTORS[actionKey];
  if (!factory) {
    throw new Error(`Unknown operator action descriptor: ${actionKey}`);
  }
  return factory(context);
}
