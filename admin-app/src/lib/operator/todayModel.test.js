import test from 'node:test';
import assert from 'node:assert/strict';

import { buildShiftKpis, buildTodayRouteModel, SHIFT_KPI_ORDER, sortCriticalIncidents } from './todayModel.js';

test('sortCriticalIncidents keeps only high/critical and sorts by priority', () => {
  const sorted = sortCriticalIncidents([
    { incident_id: 1, priority: 'high', status: 'new' },
    { incident_id: 2, priority: 'critical', status: 'in_progress' },
    { incident_id: 3, priority: 'medium', status: 'new' },
    { incident_id: 4, priority: 'critical', status: 'closed' },
  ]);

  assert.deepEqual(sorted.map((item) => item.incident_id), [2, 1]);
});

test('buildTodayRouteModel deduplicates action items and builds fallback CTA', () => {
  const model = buildTodayRouteModel({
    incidents: [],
    tapSummary: {
      attentionItems: [
        { key: 'sync-1', severity: 'warning', kind: 'unsynced_flow', title: 'Tap 1', href: '#/taps' },
        { key: 'sync-1', severity: 'warning', kind: 'unsynced_flow', title: 'Tap 1', href: '#/taps' },
      ],
    },
    taps: [],
    systemHealth: { primaryPills: [], sync: { state: 'ok' }, sections: { accumulatedIssues: { deviceCount: 0 } } },
    todaySummary: { summary_complete: true, sessions_count: 2, volume_ml: 500, revenue: 123 },
    todaySummaryError: null,
    permissions: { incidents_view: false },
    dismissedAttentionKeys: new Set(),
  });

  assert.equal(model.operatorActionItems.length, 1);
  assert.equal(model.operatorActionItems[0].key, 'next-sync-1');

  const fallback = buildTodayRouteModel({
    incidents: [],
    tapSummary: { attentionItems: [] },
    taps: [],
    systemHealth: { primaryPills: [], sync: { state: 'ok' }, sections: { accumulatedIssues: { deviceCount: 0 } } },
    todaySummary: { summary_complete: true },
    todaySummaryError: null,
    permissions: {},
    dismissedAttentionKeys: new Set(),
  });

  assert.equal(fallback.priorityCta.target, 'system');
  assert.equal(fallback.priorityCta.href, '/system');
});

test('buildShiftKpis keeps canonical KPI order for shift screen', () => {
  const kpis = buildShiftKpis({
    activeVisitCount: 4,
    pouringCount: 2,
    openIncidentCount: 1,
    volumeMl: 1200,
    revenue: 980,
  });

  assert.deepEqual(kpis.map((item) => item.key), SHIFT_KPI_ORDER);
  assert.equal(kpis[0].label, 'Активные визиты');
  assert.equal(kpis[2].label, 'Инциденты');
});
