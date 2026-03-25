import test from 'node:test';
import assert from 'node:assert/strict';

import { buildOperatorActionRequest, normalizeOperatorActionValues } from './actionDialogModel.js';

test('buildOperatorActionRequest adds reason code fields for tap stop actions', () => {
  const request = buildOperatorActionRequest({
    actionKey: 'tap.stop',
    policy: {
      allowed: true,
      confirm_required: true,
      reason_code_required: true,
    },
    context: {
      tap: { display_name: 'Tap 7' },
    },
  });

  assert.equal(request.mode, 'reason-code + comment');
  assert.match(request.title, /stop pour/i);
  assert.match(request.description, /Tap 7/);
  assert.deepEqual(request.fields.map((field) => field.name), ['reasonCode', 'comment']);
  assert.deepEqual(request.validate({ reasonCode: 'safety', comment: '' }), {});
  assert.deepEqual(request.validate({ reasonCode: 'other', comment: '' }), {
    comment: 'Comment is required for "Other".',
  });
});

test('buildOperatorActionRequest keeps incident-form fields and reports blocked reasons', () => {
  const request = buildOperatorActionRequest({
    actionKey: 'incident.close',
    policy: {
      allowed: true,
      confirm_required: true,
    },
    context: {
      incidentId: 42,
    },
    readOnlyReason: 'Incident actions are read-only right now.',
  });

  assert.equal(request.mode, 'incident-form');
  assert.equal(request.blockedReason, 'Incident actions are read-only right now.');
  assert.deepEqual(request.fields.map((field) => field.name), ['note', 'resolutionSummary']);
});

test('normalizeOperatorActionValues trims string payloads', () => {
  assert.deepEqual(normalizeOperatorActionValues({
    reasonCode: '  safety  ',
    comment: '  stopped on shift  ',
    count: 2,
  }), {
    reasonCode: 'safety',
    comment: 'stopped on shift',
    count: 2,
  });
});
