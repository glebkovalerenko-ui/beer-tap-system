export const OPERATOR_REASON_CODE_OPTIONS = Object.freeze([
  {
    value: 'safety',
    label: 'Safety',
    description: 'Use when the action protects guests, staff, or equipment.',
  },
  {
    value: 'incident-response',
    label: 'Incident response',
    description: 'Use when the action is part of incident handling on shift.',
  },
  {
    value: 'hardware-fault',
    label: 'Hardware fault',
    description: 'Use when hardware or telemetry is degraded or inconsistent.',
  },
  {
    value: 'security',
    label: 'Security',
    description: 'Use when the action is driven by fraud, card safety, or access concerns.',
  },
  {
    value: 'other',
    label: 'Other',
    description: 'Use only when none of the standard reason codes fit.',
  },
]);

export function getOperatorReasonCodeOptions() {
  return OPERATOR_REASON_CODE_OPTIONS.map((option) => ({ ...option }));
}

export function isOperatorCommentRequired(reasonCode) {
  return String(reasonCode || '').trim().toLowerCase() === 'other';
}
