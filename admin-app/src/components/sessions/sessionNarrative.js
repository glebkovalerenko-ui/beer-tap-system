export const syncLabels = {
  pending_sync: 'Ожидает синхронизации',
  rejected: 'Синхронизация отклонена',
  reconciled: 'Сверено вручную',
  synced: 'Синхронизировано',
  not_started: 'Наливов не было',
};

const narrativeKindLabels = {
  open: 'Сессия открыта',
  authorize: 'Карта подтверждена',
  pour_start: 'Налив начался',
  pour_end: 'Налив завершён',
  sync: 'Статус синхронизации обновлён',
  close: 'Сессия закрыта',
  abort: 'Сессия прервана',
  incident: 'Зафиксирован инцидент',
  action: 'Действие оператора',
};

const actionLabels = {
  force_unlock: 'Оператор принудительно разблокировал сессию',
  reconcile_pour: 'Оператор скорректировал налив',
  report_lost_card: 'Оператор отметил карту как потерянную',
  close_visit: 'Оператор завершил сессию',
  assign_card: 'Оператор привязал карту',
};

export function buildWhatHappened(summary, describeCompletionSource) {
  const lifecycle = [];
  lifecycle.push(`Сессия ${summary.operator_status?.toLowerCase() || 'обработана'}${summary.card_uid ? ` по карте ${summary.card_uid}` : ' без привязанной карты'}`);
  if (summary.taps?.length) {
    lifecycle.push(`через кран ${summary.taps.join(', ')}`);
  }
  const state = [];
  state.push(syncLabels[summary.sync_state] || summary.sync_state);
  if (summary.contains_tail_pour) state.push('зафиксирован долив хвоста');
  if (summary.contains_non_sale_flow) state.push('был служебный налив без продажи');
  if (summary.has_unsynced) state.push('остались несинхронизированные данные');
  return [
    `${lifecycle.join(' ')}.`,
    `Источник завершения: ${describeCompletionSource(summary.completion_source)}. ${state.join(', ')}.`,
  ];
}

export function fallbackNarrative(summary, describeCompletionSource) {
  const lifecycle = summary.lifecycle || {};
  return [
    lifecycle.opened_at && {
      timestamp: lifecycle.opened_at,
      title: 'Сессия открыта',
      description: 'Оператор открыл сессию и журнал начал отслеживание событий.',
      kind: 'open',
      status: summary.visit_status,
    },
    lifecycle.first_authorized_at && {
      timestamp: lifecycle.first_authorized_at,
      title: 'Карта подтверждена',
      description: summary.card_uid ? `Карта ${summary.card_uid} была подтверждена для доступа к наливу.` : 'Система подтвердила доступ к наливу.',
      kind: 'authorize',
      status: summary.visit_status,
    },
    lifecycle.first_pour_started_at && {
      timestamp: lifecycle.first_pour_started_at,
      title: 'Налив начался',
      description: 'Гость начал налив по этой сессии.',
      kind: 'pour_start',
      status: summary.visit_status,
    },
    lifecycle.last_pour_ended_at && {
      timestamp: lifecycle.last_pour_ended_at,
      title: 'Последний налив завершён',
      description: 'Последний зафиксированный налив по сессии завершился.',
      kind: 'pour_end',
      status: summary.visit_status,
    },
    lifecycle.closed_at && {
      timestamp: lifecycle.closed_at,
      title: summary.operator_status === 'Прервана' ? 'Сессия прервана' : 'Сессия завершена',
      description: `Завершение отмечено как: ${describeCompletionSource(summary.completion_source)}.`,
      kind: summary.operator_status === 'Прервана' ? 'abort' : 'close',
      status: summary.visit_status,
    },
  ].filter(Boolean);
}

export function buildDisplayContext(detailPayload) {
  const context = detailPayload?.display_context;
  if (!context?.available) {
    return {
      available: false,
      title: 'Что видел гость',
      placeholder: context?.note || 'Display context не был сохранён для этой сессии.',
      incidentLink: context?.incident_link || (detailPayload?.summary?.has_incident
        ? 'По этой сессии есть incident narrative, но связать его с экраном нельзя: display context не был сохранён.'
        : ''),
      fields: [],
      overrides: [],
      note: context?.note || '',
    };
  }

  const fields = [
    { label: 'Display state / availability', value: context.availability_label || context.display_state || '—' },
    { label: 'Guest-facing title', value: context.title || '—' },
    { label: 'Guest-facing subtitle', value: context.subtitle || '—' },
    { label: 'Maintenance режим', value: context.maintenance_mode || 'Не использовался / не восстановлен' },
    { label: 'Fallback режим', value: context.fallback_mode || 'Не использовался / не восстановлен' },
  ];

  return {
    available: true,
    title: 'Что видел гость',
    placeholder: '',
    incidentLink: context.incident_link || '',
    note: context.note || '',
    fields,
    overrides: context.important_overrides || [],
    tapLabel: context.tap_name ? `${context.tap_name}${context.tap_id ? ` · tap #${context.tap_id}` : ''}` : (context.tap_id ? `Tap #${context.tap_id}` : ''),
  };
}

export function groupedNarrative(detailPayload, formatMaybeDate, describeCompletionSource) {
  const source = detailPayload?.narrative?.length ? detailPayload.narrative : fallbackNarrative(detailPayload.summary, describeCompletionSource);
  const timeline = source.map((event) => ({
    ...event,
    title: event.title || narrativeKindLabels[event.kind] || 'Событие сессии',
    description: event.description || 'Подробности по событию система не передала.',
  }));
  const operatorObservations = [];
  if (detailPayload.summary.has_incident) operatorObservations.push({ title: 'В сессии были инциденты', description: `Количество инцидентов: ${detailPayload.summary.incident_count || 1}.` });
  if (detailPayload.summary.contains_tail_pour) operatorObservations.push({ title: 'Есть долив хвоста', description: 'Сессия включает хвостовой долив и требует внимательной проверки итогов.' });
  if (detailPayload.summary.contains_non_sale_flow) operatorObservations.push({ title: 'Есть служебный налив', description: 'Часть действий прошла как служебный налив и не должна трактоваться как обычная продажа.' });
  if (detailPayload.summary.has_unsynced) operatorObservations.push({ title: 'Есть риск несинхронизированных данных', description: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state });

  const lifecycle = detailPayload.summary.lifecycle || {};
  const lifecycleCards = [
    { label: 'Старт сессии', value: formatMaybeDate(lifecycle.opened_at), note: 'Источник: открытие визита / старт workflow' },
    { label: 'Источник завершения', value: describeCompletionSource(detailPayload.summary.completion_source), note: 'Окончание сессии или причина прерывания' },
    { label: 'Синхронизация', value: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state, note: formatMaybeDate(lifecycle.last_sync_at) },
    { label: 'Хвостовой долив', value: detailPayload.summary.contains_tail_pour ? 'Да' : 'Нет', note: detailPayload.summary.contains_tail_pour ? 'Нужна проверка хвостового долива' : 'Хвостовой долив не найден' },
    { label: 'Служебный налив', value: detailPayload.summary.contains_non_sale_flow ? 'Да' : 'Нет', note: detailPayload.summary.contains_non_sale_flow ? 'Был служебный налив без продажи' : 'Служебных наливов нет' },
    { label: 'Финиш сессии', value: formatMaybeDate(lifecycle.closed_at), note: `Последний налив: ${formatMaybeDate(lifecycle.last_pour_ended_at)}` },
  ];

  return { timeline, operatorObservations, lifecycleCards };
}

export function normalizedOperatorActions(summary, describeCompletionSource, describeFlags) {
  if (summary.operator_actions?.length) {
    return summary.operator_actions.map((action) => ({
      ...action,
      label: action.label || actionLabels[action.action] || action.action?.replaceAll('_', ' ') || 'Действие оператора',
      details: action.details || 'Система не передала дополнительный комментарий.',
    }));
  }
  if (summary.completion_source || summary.contains_tail_pour || summary.contains_non_sale_flow) {
    return [{
      timestamp: summary.closed_at || summary.last_event_at || summary.opened_at,
      label: 'Клиент собрал краткое резюме действий',
      details: `Источник завершения: ${describeCompletionSource(summary.completion_source)}. ${describeFlags(summary)}.`,
    }];
  }
  return [];
}
