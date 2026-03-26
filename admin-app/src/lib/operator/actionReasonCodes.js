export const OPERATOR_REASON_CODE_OPTIONS = Object.freeze([
  {
    value: 'safety',
    label: 'Безопасность',
    description: 'Используйте, когда действие защищает гостя, команду или оборудование.',
  },
  {
    value: 'incident-response',
    label: 'Разбор инцидента',
    description: 'Используйте, когда действие является частью разбора инцидента на смене.',
  },
  {
    value: 'hardware-fault',
    label: 'Сбой оборудования',
    description: 'Используйте, когда оборудование или телеметрия работают нестабильно.',
  },
  {
    value: 'security',
    label: 'Контроль доступа',
    description: 'Используйте, когда действие связано с мошенничеством, безопасностью карты или доступом.',
  },
  {
    value: 'other',
    label: 'Другое',
    description: 'Используйте только если стандартные причины не подходят.',
  },
]);

export function getOperatorReasonCodeOptions() {
  return OPERATOR_REASON_CODE_OPTIONS.map((option) => ({ ...option }));
}

export function isOperatorCommentRequired(reasonCode) {
  return String(reasonCode || '').trim().toLowerCase() === 'other';
}
