const ROLE_LABELS = {
  operator: 'Оператор',
  shift_lead: 'Старший смены',
  engineer_owner: 'Инженер / владелец',
};

export const CRITICAL_ACTION_MATRIX = {
  stop_pour: {
    label: 'Stop pour',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Остановить налив может только старший смены или инженер.',
  },
  block_unblock_tap: {
    label: 'Block/unblock tap',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Блокировка и разблокировка крана доступны только ролям с taps_control.',
  },
  close_incident: {
    label: 'Close incident',
    permission: 'incidents_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'show_disabled',
    deniedReason: 'Закрытие инцидента доступно только роли с incidents_manage.',
  },
  escalate_incident: {
    label: 'Escalate incident',
    permission: 'incidents_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'show_disabled',
    deniedReason: 'Эскалация инцидента доступна только роли с incidents_manage.',
  },
  mark_lost_reissue: {
    label: 'Mark lost / reissue',
    permission: 'cards_reissue_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Lost/перевыпуск доступен только ролям с cards_reissue_manage.',
  },
  block_unblock_card: {
    label: 'Block/unblock card',
    permission: 'cards_block_manage',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: false,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Блокировка карты доступна только ролям с cards_block_manage.',
  },
  keg_connect_disconnect: {
    label: 'Keg connect/disconnect',
    permission: 'taps_control',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Подключать/отключать кеги могут только роли с taps_control.',
  },
  display_override: {
    label: 'Display override',
    permission: 'display_override',
    roles: ['engineer_owner'],
    requiresTwoStep: false,
    requiresComment: false,
    uiVisibility: 'hidden',
    deniedReason: 'Управление guest display доступно только инженеру/владельцу.',
  },
  maintenance_toggle: {
    label: 'Maintenance state toggles',
    permission: 'maintenance_actions',
    roles: ['shift_lead', 'engineer_owner'],
    requiresTwoStep: true,
    requiresComment: false,
    uiVisibility: 'show_disabled',
    deniedReason: 'Сервисные переключения доступны только сервисным ролям.',
  },
  system_diagnostics_action: {
    label: 'System diagnostics actions',
    permission: 'system_engineering_actions',
    roles: ['engineer_owner'],
    requiresTwoStep: true,
    requiresComment: true,
    uiVisibility: 'hidden',
    deniedReason: 'Инженерная диагностика доступна только инженеру/владельцу.',
  },
};

export function getCriticalActionGuard(actionKey, permissions = {}, options = {}) {
  const spec = CRITICAL_ACTION_MATRIX[actionKey];
  if (!spec) {
    return {
      visible: true,
      disabled: false,
      reason: '',
      allowed: true,
      spec: null,
    };
  }

  const permissionAllowed = Boolean(permissions?.[spec.permission]);
  const extraAllowed = options.extraAllowed !== false;
  const allowed = permissionAllowed && extraAllowed;
  const reason = options.reason || (!permissionAllowed ? spec.deniedReason : options.extraDeniedReason || 'Действие сейчас недоступно.');

  return {
    visible: allowed || spec.uiVisibility !== 'hidden',
    disabled: !allowed,
    reason: !allowed ? reason : '',
    allowed,
    spec,
  };
}

export function buildCriticalActionRows() {
  return Object.entries(CRITICAL_ACTION_MATRIX).map(([key, spec]) => ({
    key,
    action: spec.label,
    requiredRole: spec.roles.map((role) => ROLE_LABELS[role] || role).join(' / '),
    requiresTwoStep: spec.requiresTwoStep,
    requiresComment: spec.requiresComment,
    uiVisibility: spec.uiVisibility === 'hidden' ? 'Скрыто при отсутствии прав' : 'Показывается disabled + reason',
  }));
}
