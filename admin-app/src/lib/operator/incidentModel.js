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
