export const syncLabels = {
  pending_sync: 'Ожидает синхронизацию',
  rejected: 'Синхронизация отклонена',
  reconciled: 'Сверено вручную',
  synced: 'Синхронизировано',
  not_started: 'Наливов не было',
};

const narrativeKindLabels = {
  open: 'Визит открыт',
  authorize: 'Карта подтверждена',
  pour_start: 'Налив начался',
  pour_end: 'Налив завершён',
  sync: 'Статус синхронизации обновлён',
  close: 'Визит закрыт',
  abort: 'Визит прерван',
  incident: 'Зафиксирован инцидент',
  action: 'Действие оператора',
};

const actionLabels = {
  force_unlock: 'Оператор снял блокировку визита',
  reconcile_pour: 'Оператор выполнил ручную сверку налива',
  report_lost_card: 'Оператор отметил карту как потерянную',
  close_visit: 'Оператор завершил визит',
  assign_card: 'Оператор привязал карту',
};

export function buildWhatHappened(summary, describeCompletionSource) {
  const lifecycle = [];
  lifecycle.push(`Визит ${summary.operator_status?.toLowerCase() || 'обработан'}${summary.card_uid ? ` по карте ${summary.card_uid}` : ' без привязанной карты'}`);
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
      title: 'Визит открыт',
      description: 'Оператор открыл визит, и журнал начал отслеживать события по гостю.',
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
      description: 'Гость начал налив в рамках этого визита.',
      kind: 'pour_start',
      status: summary.visit_status,
    },
    lifecycle.last_pour_ended_at && {
      timestamp: lifecycle.last_pour_ended_at,
      title: 'Последний налив завершён',
      description: 'Последний зафиксированный налив по визиту завершился.',
      kind: 'pour_end',
      status: summary.visit_status,
    },
    lifecycle.closed_at && {
      timestamp: lifecycle.closed_at,
      title: summary.operator_status === 'Заблокирован' ? 'Визит заблокирован' : 'Визит завершён',
      description: `Завершение отмечено как: ${describeCompletionSource(summary.completion_source)}.`,
      kind: summary.operator_status === 'Заблокирован' ? 'abort' : 'close',
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
      placeholder: context?.note || 'Display context не был сохранён для этого визита.',
      incidentLink: context?.incident_link || (detailPayload?.summary?.has_incident
        ? 'По этому визиту есть incident narrative, но display context не был сохранён.'
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
    { label: 'Maintenance mode', value: context.maintenance_mode || 'Не использовался / не восстановлен' },
    { label: 'Fallback mode', value: context.fallback_mode || 'Не использовался / не восстановлен' },
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
    title: event.title || narrativeKindLabels[event.kind] || 'Событие визита',
    description: event.description || 'Система не передала дополнительные подробности.',
  }));
  const operatorObservations = [];
  if (detailPayload.summary.has_incident) operatorObservations.push({ title: 'В визите были инциденты', description: `Количество инцидентов: ${detailPayload.summary.incident_count || 1}.` });
  if (detailPayload.summary.contains_tail_pour) operatorObservations.push({ title: 'Есть долив хвоста', description: 'Визит включает хвостовой долив и требует внимательной проверки итогов.' });
  if (detailPayload.summary.contains_non_sale_flow) operatorObservations.push({ title: 'Есть служебный налив', description: 'Часть действий прошла как служебный налив и не должна трактоваться как обычная продажа.' });
  if (detailPayload.summary.has_unsynced) operatorObservations.push({ title: 'Есть риск несинхронизированных данных', description: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state });

  const lifecycle = detailPayload.summary.lifecycle || {};
  const lifecycleCards = [
    { label: 'Старт визита', value: formatMaybeDate(lifecycle.opened_at), note: 'Источник: открытие визита / старт operator workflow' },
    { label: 'Источник завершения', value: describeCompletionSource(detailPayload.summary.completion_source), note: 'Окончание визита или причина прерывания' },
    { label: 'Синхронизация', value: syncLabels[detailPayload.summary.sync_state] || detailPayload.summary.sync_state, note: formatMaybeDate(lifecycle.last_sync_at) },
    { label: 'Хвостовой долив', value: detailPayload.summary.contains_tail_pour ? 'Да' : 'Нет', note: detailPayload.summary.contains_tail_pour ? 'Нужна проверка хвостового долива' : 'Хвостовой долив не найден' },
    { label: 'Служебный налив', value: detailPayload.summary.contains_non_sale_flow ? 'Да' : 'Нет', note: detailPayload.summary.contains_non_sale_flow ? 'Был служебный налив без продажи' : 'Служебных наливов нет' },
    { label: 'Финиш визита', value: formatMaybeDate(lifecycle.closed_at), note: `Последний налив: ${formatMaybeDate(lifecycle.last_pour_ended_at)}` },
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
      label: 'Краткое резюме действий',
      details: `Источник завершения: ${describeCompletionSource(summary.completion_source)}. ${describeFlags(summary)}.`,
    }];
  }
  return [];
}
