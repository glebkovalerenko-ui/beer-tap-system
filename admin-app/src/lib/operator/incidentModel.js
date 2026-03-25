export function buildIncidentCapabilities(capabilitiesRaw = {}) {
  return {
    capabilities: {
      claim: Boolean(capabilitiesRaw.claim?.enabled),
      escalate: Boolean(capabilitiesRaw.escalate?.enabled),
      close: Boolean(capabilitiesRaw.close?.enabled),
      note: Boolean(capabilitiesRaw.note?.enabled),
    },
    reasons: {
      claim: capabilitiesRaw.claim?.reason || null,
      escalate: capabilitiesRaw.escalate?.reason || null,
      close: capabilitiesRaw.close?.reason || null,
      note: capabilitiesRaw.note?.reason || null,
    },
  };
}

export function resolveIncidentAction({ suggestedAction = 'note', capabilities }) {
  const allowedActions = ['claim', 'note', 'escalate', 'close'].filter((action) => capabilities?.[action]);
  return allowedActions.includes(suggestedAction)
    ? suggestedAction
    : (allowedActions[0] || 'note');
}

export function buildIncidentActionCopy(action) {
  if (action === 'claim') {
    return {
      heading: 'Взять инцидент в работу',
      intro: 'Назначьте ответственного и зафиксируйте первый шаг, чтобы очередь смены сразу показала, кто ведёт разбор.',
      noteLabel: 'Что делаем первым',
      notePlaceholder: 'Что уже проверили, что увидели на месте и с какого шага начинаете разбор.',
      secondaryLabel: 'Ответственный',
      secondaryPlaceholder: 'Имя оператора или старшего смены',
      secondaryHelp: 'Этот человек будет показан в очереди как ведущий разбор.',
    };
  }

  if (action === 'escalate') {
    return {
      heading: 'Передать на разбор',
      intro: 'Опишите, кому и почему передаёте кейс, чтобы следующий человек получил контекст без повторного поиска.',
      noteLabel: 'Что уже проверили',
      notePlaceholder: 'Какие шаги уже выполнены и что удалось подтвердить до эскалации.',
      secondaryLabel: 'Причина эскалации',
      secondaryPlaceholder: 'Почему нужен следующий уровень разбора и что именно мешает закрыть кейс на смене.',
      secondaryHelp: 'Коротко зафиксируйте, что требуется от следующего уровня поддержки.',
    };
  }

  if (action === 'close') {
    return {
      heading: 'Закрыть инцидент',
      intro: 'Подтвердите, как именно проблема была снята, чтобы карточка инцидента показывала понятный итог для смены.',
      noteLabel: 'Что сделали',
      notePlaceholder: 'Какие действия выполнили перед закрытием и что увидели после проверки.',
      secondaryLabel: 'Итог решения',
      secondaryPlaceholder: 'Почему проблему можно считать закрытой и чем это подтверждено.',
      secondaryHelp: 'Этот итог будет основой финальной записи по инциденту.',
    };
  }

  return {
    heading: 'Добавить заметку',
    intro: 'Коротко зафиксируйте наблюдение или шаг оператора, чтобы следующий участник очереди увидел контекст.',
    noteLabel: 'Заметка оператора',
    notePlaceholder: 'Что увидели, что проверили и что важно не потерять при следующем открытии кейса.',
    secondaryLabel: '',
    secondaryPlaceholder: '',
    secondaryHelp: '',
  };
}

export function resolveIncidentActionRequest({ action, item, form }) {
  if (action === 'claim') {
    return {
      method: 'claimIncident',
      payload: {
        incidentId: item.incident_id,
        owner: form.owner.trim(),
        note: form.note.trim() || null,
      },
    };
  }

  if (action === 'escalate') {
    return {
      method: 'escalateIncident',
      payload: {
        incidentId: item.incident_id,
        reason: form.escalationReason.trim(),
        note: form.note.trim() || null,
      },
    };
  }

  if (action === 'close') {
    return {
      method: 'closeIncident',
      payload: {
        incidentId: item.incident_id,
        resolutionSummary: form.resolutionSummary.trim(),
        note: form.note.trim() || null,
      },
    };
  }

  return {
    method: 'addIncidentNote',
    payload: {
      incidentId: item.incident_id,
      note: form.note.trim(),
    },
  };
}
