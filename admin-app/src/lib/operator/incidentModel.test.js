import test from 'node:test';
import assert from 'node:assert/strict';

import { buildIncidentCapabilities, resolveIncidentAction, resolveIncidentActionRequest } from './incidentModel.js';

test('buildIncidentCapabilities maps enabled flags and reasons', () => {
  const model = buildIncidentCapabilities({
    claim: { enabled: true, reason: null },
    close: { enabled: false, reason: 'readonly' },
  });

  assert.equal(model.capabilities.claim, true);
  assert.equal(model.capabilities.close, false);
  assert.equal(model.reasons.close, 'readonly');
  assert.equal(model.reasons.note, null);
});

test('resolveIncidentAction respects capability gating fallback order', () => {
  const selected = resolveIncidentAction({
    suggestedAction: 'close',
    capabilities: { claim: false, note: true, escalate: true, close: false },
  });
  assert.equal(selected, 'note');
});

test('resolveIncidentActionRequest routes to proper store method', () => {
  const base = { item: { incident_id: 77 }, form: { owner: '  Alex  ', note: '  hi ', escalationReason: '  need help  ', resolutionSummary: '  fixed  ' } };

  const claim = resolveIncidentActionRequest({ ...base, action: 'claim' });
  assert.equal(claim.method, 'claimIncident');
  assert.deepEqual(claim.payload, { incidentId: 77, owner: 'Alex', note: 'hi' });

  const escalate = resolveIncidentActionRequest({ ...base, action: 'escalate' });
  assert.equal(escalate.method, 'escalateIncident');
  assert.deepEqual(escalate.payload, { incidentId: 77, reason: 'need help', note: 'hi' });

  const close = resolveIncidentActionRequest({ ...base, action: 'close' });
  assert.equal(close.method, 'closeIncident');
  assert.deepEqual(close.payload, { incidentId: 77, resolutionSummary: 'fixed', note: 'hi' });

  const note = resolveIncidentActionRequest({ ...base, action: 'note' });
  assert.equal(note.method, 'addIncidentNote');
  assert.deepEqual(note.payload, { incidentId: 77, note: 'hi' });
});
