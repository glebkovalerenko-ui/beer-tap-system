import test from 'node:test';
import assert from 'node:assert/strict';

import { buildEnrichedIncidents, filterIncidents, groupIncidentsByStatus } from './incidentsViewModel.js';

const BASE_ARGS = {
  taps: [{
    tap_id: 7,
    display_name: 'Кран 7',
    operations: {
      operatorHistory: [
        {
          id: 'dup-1',
          title: 'Нет связи со считывателем',
          description: 'Считыватель не отвечает',
          happenedAt: '2026-03-26T10:00:00.000Z',
          sessionAction: { href: '#/visits', label: 'Открыть визит', visitId: 'v-1' },
        },
        {
          id: 'dup-2',
          title: 'Нет связи со считывателем',
          description: 'Считыватель не отвечает',
          happenedAt: '2026-03-26T10:00:00.000Z',
          sessionAction: { href: '#/visits', label: 'Открыть визит', visitId: 'v-1' },
        },
      ],
      currentPour: { isActive: true },
      heartbeat: { isStale: true, minutesAgo: 8, at: '2026-03-26T10:02:00.000Z' },
    },
  }],
  activeVisits: [{
    visit_id: 'v-1',
    taps: ['7'],
    guest_full_name: 'Иван Петров',
    operator_status: 'Требует внимания',
    has_incident: true,
    incident_count: 1,
    last_event_at: '2026-03-26T10:03:00.000Z',
  }],
  systemState: 'warning',
  openIncidentCount: 1,
  incidentCopy: { openTap: 'Открыть кран', openSystem: 'Открыть систему' },
  priorityLabels: { critical: 'Критический', high: 'Высокий' },
  statusLabels: { new: 'Новый', in_progress: 'В работе', closed: 'Закрыт' },
};

test('buildEnrichedIncidents adds canonical severity, aging cue and deduped related events', () => {
  const items = buildEnrichedIncidents({
    ...BASE_ARGS,
    incidents: [{
      incident_id: 101,
      tap: '7',
      type: 'reader_offline',
      priority: 'critical',
      severity: 'S1',
      status: 'new',
      created_at: '2026-03-26T10:00:00.000Z',
      acknowledge_deadline_at: '2026-03-26T09:50:00.000Z',
    }],
  });

  assert.equal(items[0].uiSeverity, 'critical');
  assert.equal(items[0].uiSeverityLabel, 'Критично');
  assert.equal(items[0].agingCue, 'overdue');
  assert.equal(items[0].relatedEvents.length, 2);
  assert.match(items[0].relatedEvents[0].description, /Повторилось 2 раза/);
});

test('filterIncidents keeps at-risk incidents when SLA filter is active', () => {
  const items = buildEnrichedIncidents({
    ...BASE_ARGS,
    incidents: [{
      incident_id: 102,
      tap: '7',
      type: 'reader_offline',
      priority: 'high',
      severity: 'S2',
      status: 'in_progress',
      created_at: '2026-03-26T10:00:00.000Z',
      sla_at_risk: true,
    }],
  });

  const filtered = filterIncidents(items, {
    priority: 'all',
    status: 'all',
    type: 'all',
    tap: 'all',
    time: 'all',
    query: '',
    slaRisk: 'at_risk',
  });

  assert.equal(filtered.length, 1);
  assert.ok(['aging', 'overdue'].includes(filtered[0].agingCue));
});

test('groupIncidentsByStatus keeps open incidents ahead of closed ones', () => {
  const items = buildEnrichedIncidents({
    ...BASE_ARGS,
    incidents: [
      {
        incident_id: 201,
        tap: '7',
        type: 'reader_offline',
        priority: 'high',
        severity: 'S2',
        status: 'new',
        created_at: '2026-03-26T10:00:00.000Z',
      },
      {
        incident_id: 202,
        tap: '7',
        type: 'reader_offline',
        priority: 'high',
        severity: 'S2',
        status: 'closed',
        created_at: '2026-03-26T09:00:00.000Z',
      },
    ],
  });

  const grouped = groupIncidentsByStatus(items, { new: 'Новые', in_progress: 'В работе', closed: 'Закрытые' });
  assert.equal(grouped[0].items[0].incident_id, 201);
  assert.equal(grouped[2].items[0].entryKind, 'event');
});
