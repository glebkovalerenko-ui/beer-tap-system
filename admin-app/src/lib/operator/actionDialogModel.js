import { getOperatorReasonCodeOptions, isOperatorCommentRequired } from './actionReasonCodes.js';
import { resolveActionBlockState } from './actionPolicyAdapter.js';
import { getOperatorActionDescriptor } from './actionDescriptors.js';

function trimString(value) {
  return typeof value === 'string' ? value.trim() : value;
}

function buildInitialValues(fields = []) {
  return Object.fromEntries(fields.map((field) => [field.name, field.initialValue ?? '']));
}

function buildReasonFields(descriptor = {}) {
  return [
    {
      name: 'reasonCode',
      label: 'Reason code',
      type: 'select',
      required: true,
      options: getOperatorReasonCodeOptions().map((option) => ({
        value: option.value,
        label: option.label,
        description: option.description,
      })),
      initialValue: descriptor.defaultReasonCode || '',
    },
    {
      name: 'comment',
      label: 'Comment',
      type: 'textarea',
      rows: 4,
      placeholder: 'Operator context for the audit trail',
      initialValue: '',
    },
  ];
}

export function buildOperatorActionRequest({
  actionKey,
  policy,
  context = {},
  readOnlyReason = '',
  overrides = {},
}) {
  const blockState = resolveActionBlockState(policy, readOnlyReason);
  const descriptor = { ...getOperatorActionDescriptor(actionKey, context), ...overrides };
  const reasonFields = blockState.policy.reasonCodeRequired ? buildReasonFields(descriptor) : [];
  const fields = [...(descriptor.fields || []), ...reasonFields];
  const mode = descriptor.mode || (reasonFields.length > 0 ? 'reason-code + comment' : 'confirm-only');

  return {
    mode,
    blockedReason: blockState.reason,
    normalizedPolicy: blockState.policy,
    title: descriptor.title,
    description: descriptor.description,
    submitText: descriptor.submitText || 'Confirm',
    cancelText: descriptor.cancelText || 'Cancel',
    danger: Boolean(descriptor.danger),
    successMessage: descriptor.successMessage || '',
    fields,
    initialValues: {
      ...buildInitialValues(fields),
      ...(descriptor.initialValues || {}),
    },
    validate(values = {}) {
      const errors = {};
      for (const field of fields) {
        const rawValue = values[field.name];
        const normalizedValue = typeof rawValue === 'string' ? rawValue.trim() : rawValue;
        if (field.required && `${normalizedValue ?? ''}` === '') {
          errors[field.name] = 'This field is required.';
          continue;
        }
        if (field.type === 'number' && `${normalizedValue ?? ''}` !== '') {
          const parsed = Number(normalizedValue);
          if (!Number.isFinite(parsed)) {
            errors[field.name] = 'Enter a valid number.';
            continue;
          }
          if (typeof field.min === 'number' && parsed < field.min) {
            errors[field.name] = `Value must be at least ${field.min}.`;
          }
        }
      }

      if (blockState.policy.reasonCodeRequired) {
        const reasonCode = trimString(values.reasonCode);
        if (!reasonCode) {
          errors.reasonCode = 'Select a reason code.';
        }
        if (isOperatorCommentRequired(reasonCode) && !trimString(values.comment)) {
          errors.comment = 'Comment is required for "Other".';
        }
      }

      const descriptorErrors = descriptor.validate ? descriptor.validate(values, context) : null;
      if (descriptorErrors && typeof descriptorErrors === 'object') {
        Object.assign(errors, descriptorErrors);
      }

      return errors;
    },
  };
}

export function normalizeOperatorActionValues(values = {}) {
  return Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, trimString(value)])
  );
}
