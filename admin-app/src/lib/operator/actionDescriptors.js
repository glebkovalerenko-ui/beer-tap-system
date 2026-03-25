function tapName(context = {}) {
  return context.tap?.display_name || context.tapName || 'this tap';
}

function sessionName(context = {}) {
  return context.sessionLabel || (context.visitId ? `session #${context.visitId}` : 'this session');
}

function guestName(context = {}) {
  return context.guestName || 'this guest';
}

function incidentName(context = {}) {
  return context.incidentId ? `incident #${context.incidentId}` : 'this incident';
}

const OPERATOR_ACTION_DESCRIPTORS = {
  'session.close': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Close session',
    description: `Close ${sessionName(context)} and refresh it in the operator journal.`,
    submitText: 'Close session',
    successMessage: 'Session closed.',
    danger: true,
    defaultReasonCode: 'incident-response',
  }),
  'session.force_unlock': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Force unlock session',
    description: `Remove the lock from ${sessionName(context)} and record operator intervention.`,
    submitText: 'Force unlock',
    successMessage: 'Session unlocked.',
    defaultReasonCode: 'hardware-fault',
  }),
  'session.mark_lost_card': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Mark card as lost',
    description: `Move ${sessionName(context)} into the lost-card flow so the card can be restored or reissued safely.`,
    submitText: 'Mark lost',
    successMessage: 'Card marked as lost.',
    danger: true,
    defaultReasonCode: 'security',
  }),
  'session.reconcile': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Reconcile pour manually',
    description: `Store a manual reconcile entry for ${sessionName(context)}.`,
    submitText: 'Save reconcile',
    successMessage: 'Pour reconciled manually.',
    defaultReasonCode: 'incident-response',
    fields: [
      {
        name: 'tapId',
        label: 'Tap ID',
        type: 'number',
        required: true,
        min: 1,
        step: 1,
        initialValue: context.defaultTapId ?? '',
      },
      {
        name: 'shortId',
        label: 'Short ID',
        type: 'text',
        required: true,
        placeholder: '6-8 chars',
        initialValue: '',
      },
      {
        name: 'volumeMl',
        label: 'Volume, ml',
        type: 'number',
        required: true,
        min: 1,
        step: 1,
        initialValue: '250',
      },
      {
        name: 'amount',
        label: 'Amount',
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
        errors.shortId = 'Use 6-8 letters or numbers.';
      }
      const amount = Number(values.amount);
      if (!Number.isFinite(amount) || amount < 0) {
        errors.amount = 'Enter a valid amount.';
      }
      return errors;
    },
  }),
  'tap.stop': (context = {}) => ({
    mode: 'reason-code + comment',
    title: 'Stop pour and lock tap',
    description: `Stop the active pour on ${tapName(context)} and move the tap to a locked state.`,
    submitText: 'Stop pour',
    successMessage: 'Tap status updated.',
    danger: true,
    defaultReasonCode: 'safety',
  }),
  'tap.lock': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Lock tap',
    description: `Block ${tapName(context)} until the issue is resolved.`,
    submitText: 'Lock tap',
    successMessage: 'Tap status updated.',
  }),
  'tap.unlock': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Unlock tap',
    description: `Return ${tapName(context)} to an active state.`,
    submitText: 'Unlock tap',
    successMessage: 'Tap status updated.',
  }),
  'tap.cleaning': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Move tap to cleaning',
    description: `Switch ${tapName(context)} into cleaning mode.`,
    submitText: 'Start cleaning',
    successMessage: 'Tap status updated.',
  }),
  'tap.mark_ready': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Return tap to ready',
    description: `Return ${tapName(context)} to the ready state after service work.`,
    submitText: 'Mark ready',
    successMessage: 'Tap status updated.',
  }),
  'card.toggle_block': (context = {}) => ({
    mode: 'confirm-only',
    title: context.isActive ? 'Block guest' : 'Unblock guest',
    description: context.isActive
      ? `Block ${guestName(context)} in the operator flow until the issue is reviewed.`
      : `Restore ${guestName(context)} to active status.`,
    submitText: context.isActive ? 'Block guest' : 'Unblock guest',
    successMessage: context.isActive ? 'Guest blocked.' : 'Guest unblocked.',
    danger: Boolean(context.isActive),
  }),
  'card.mark_lost': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Mark card as lost',
    description: `Move ${guestName(context)} into the lost-card flow so the visit can be continued through reissue.`,
    submitText: 'Mark lost',
    successMessage: 'Card marked as lost.',
    danger: true,
  }),
  'card.restore_lost': (context = {}) => ({
    mode: 'confirm-only',
    title: 'Restore lost card',
    description: `Remove the lost flag for ${guestName(context)} and return the card to the normal workflow.`,
    submitText: 'Restore card',
    successMessage: 'Lost mark removed.',
  }),
  'incident.claim': (context = {}) => ({
    mode: 'incident-form',
    title: 'Claim incident',
    description: `Assign an owner and capture the first operator step for ${incidentName(context)}.`,
    submitText: 'Save action',
    successMessage: 'Incident action saved.',
    fields: [
      {
        name: 'owner',
        label: 'Owner',
        type: 'text',
        required: true,
        placeholder: 'Operator or shift lead',
        initialValue: context.owner || '',
      },
      {
        name: 'note',
        label: 'First step',
        type: 'textarea',
        rows: 5,
        placeholder: 'What did you already verify?',
        initialValue: context.note || '',
      },
    ],
  }),
  'incident.note': (context = {}) => ({
    mode: 'incident-form',
    title: 'Add incident note',
    description: `Capture the latest operator observation for ${incidentName(context)}.`,
    submitText: 'Save action',
    successMessage: 'Incident action saved.',
    fields: [
      {
        name: 'note',
        label: 'Operator note',
        type: 'textarea',
        rows: 5,
        required: true,
        placeholder: 'What changed and what should the next operator know?',
        initialValue: context.note || '',
      },
    ],
  }),
  'incident.escalate': (context = {}) => ({
    mode: 'incident-form',
    title: 'Escalate incident',
    description: `Explain what was checked and why ${incidentName(context)} needs escalation.`,
    submitText: 'Save action',
    successMessage: 'Incident action saved.',
    fields: [
      {
        name: 'note',
        label: 'What was checked',
        type: 'textarea',
        rows: 4,
        placeholder: 'Checks already completed on shift.',
        initialValue: context.note || '',
      },
      {
        name: 'escalationReason',
        label: 'Escalation reason',
        type: 'textarea',
        rows: 4,
        required: true,
        placeholder: 'Why is the next level needed?',
        initialValue: context.escalationReason || '',
      },
    ],
  }),
  'incident.close': (context = {}) => ({
    mode: 'incident-form',
    title: 'Close incident',
    description: `Record the final outcome for ${incidentName(context)}.`,
    submitText: 'Save action',
    successMessage: 'Incident action saved.',
    fields: [
      {
        name: 'note',
        label: 'What was done',
        type: 'textarea',
        rows: 4,
        placeholder: 'Steps completed before closing.',
        initialValue: context.note || '',
      },
      {
        name: 'resolutionSummary',
        label: 'Resolution summary',
        type: 'textarea',
        rows: 4,
        required: true,
        placeholder: 'Why can the incident be considered closed?',
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
