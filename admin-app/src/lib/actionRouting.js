export const ACTION_LABELS = {
  tap: 'Открыть кран',
  session: 'Открыть сессию',
  incident: 'Открыть инцидент',
  assignOwner: 'Назначить ответственного',
  checkSync: 'Проверить sync',
  system: 'Открыть систему',
  context: 'Открыть контекст',
};

const ACTION_MAP = {
  no_keg: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Открыть кран и назначить кегу',
  },
  stale_heartbeat: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.assignOwner },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить связь на месте и зафиксировать шаг',
  },
  unsynced_flow: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.checkSync,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Ответственный по смене',
    recommendedActionState: 'Проверить sync и подтвердить влияние на кран',
  },
  reader_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить считыватель и статус синхронизации',
  },
  display_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить экран и синхронизацию контента',
  },
  controller_offline: {
    primaryTarget: 'tap',
    primaryCta: ACTION_LABELS.tap,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.assignOwner },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Проверить контроллер и перевести кейс в работу',
  },
  backend_offline: {
    primaryTarget: 'incident',
    primaryCta: ACTION_LABELS.incident,
    secondaryCta: { target: 'system', label: ACTION_LABELS.checkSync },
    recommendedOwnerState: 'Назначить ответственного',
    recommendedActionState: 'Зафиксировать инцидент и проверить sync',
  },
  sync_offline: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.checkSync,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Ответственный по смене',
    recommendedActionState: 'Проверить sync и эскалировать при задержке',
  },
  incident: {
    primaryTarget: 'incident',
    primaryCta: ACTION_LABELS.incident,
    secondaryCta: { target: 'tap', label: ACTION_LABELS.tap },
    recommendedOwnerState: 'Назначить ответственного',
    recommendedActionState: 'Перевести инцидент в работу и зафиксировать шаг',
  },
  default: {
    primaryTarget: 'system',
    primaryCta: ACTION_LABELS.system,
    secondaryCta: { target: 'incident', label: ACTION_LABELS.incident },
    recommendedOwnerState: 'Нужен ответственный',
    recommendedActionState: 'Открыть контекст и выбрать следующий шаг',
  },
};

export function getActionPlan(problemKind = 'default') {
  return ACTION_MAP[problemKind] || ACTION_MAP.default;
}

export function navigateWithFocus({
  target,
  tapId = null,
  visitId = null,
  source = null,
  incidentId = null,
  href = null,
} = {}) {
  if (tapId) {
    sessionStorage.setItem('incidents.focusTapId', String(tapId));
  }
  if (visitId) {
    sessionStorage.setItem('visits.lookupVisitId', String(visitId));
  }
  if (source) {
    sessionStorage.setItem('system.focusSource', String(source));
    sessionStorage.setItem('incidents.focusSource', String(source));
  }
  if (incidentId) {
    sessionStorage.setItem('incidents.focusIncidentId', String(incidentId));
  }

  if (target === 'tap') {
    window.location.hash = '/taps';
    return;
  }
  if (target === 'session') {
    window.location.hash = '/sessions';
    return;
  }
  if (target === 'incident') {
    window.location.hash = '/incidents';
    return;
  }
  if (target === 'system') {
    window.location.hash = '/system';
    return;
  }

  window.location.hash = href || '/today';
}
