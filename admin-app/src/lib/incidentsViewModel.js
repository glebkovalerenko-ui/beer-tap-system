/**
 * @typedef {'new'|'in_progress'|'closed'} IncidentStatus
 */

/**
 * @typedef {{
 *  incident_id: string|number,
 *  tap?: string,
 *  type?: string,
 *  priority?: string,
 *  status?: IncidentStatus|string,
 *  source?: string,
 *  created_at?: string,
 *  owner?: string,
 *  operator?: string,
 *  escalated_at?: string,
 *  last_action?: string,
 *  note_action?: string,
 *  last_action_at?: string,
 *  closed_at?: string,
 *  severity?: 'S1'|'S2'|'S3'|'S4'|string,
 *  acknowledge_deadline_at?: string,
 *  closure_deadline_at?: string,
 *  sla_at_risk?: boolean
 * }} IncidentLike
 */

/** @typedef {{ tap_id?: string|number, display_name?: string, operations?: any, keg?: any, status?: string }} TapLike */
/** @typedef {{ visit_id?: string|number, taps?: Array<string|number>, active_tap_id?: string|number, operator_name?: string, operator_status?: string, guest_full_name?: string, has_incident?: boolean, incident_count?: number, opened_at?: string, last_event_at?: string }} VisitLike */

/** @typedef {{ owner: string|null, ownerLabel: string, ownerBadge: string, ownerState: string, acknowledgedAt: string|null, lastEscalatedAt: string|null, closedAt: string|null, lastActionLabel: string, nextStep: string, stateFlow: Array<{key: IncidentStatus, label: string, description: string, active: boolean, done: boolean}> }} IncidentAccountability */

/** @typedef {{
 * tapLabel: string,
 * tapId: string|number|null,
 * tapHref: string|null,
 * sessionMatch: VisitLike|null,
 * sessionHref: string,
 * systemHref: string,
 * sourceLabel: string,
 * typeLabel: string,
 * priorityLabel: string,
 * statusLabel: string,
 * operatorInitials: string,
 * accountability: IncidentAccountability,
 * summary: string,
 * narrative: string[],
 * impact: string[],
 * relatedEvents: any[],
 * actionsTaken: any[],
 * tapContext: TapLike|null,
 * systemState: string,
 * openIncidentCount: number,
 * backendStatusIsAuthoritative: true,
 * uiSeverity: 'info'|'warning'|'critical',
 * uiSeverityLabel: string,
 * agingCue: 'new'|'aging'|'overdue',
 * agingCueLabel: string,
 * requiresAction: boolean,
 * entryKind: 'incident'|'event',
 * dedupeFingerprint: string
 * } & IncidentLike} IncidentViewModel
 */

export const SECTION_ORDER = ['new', 'in_progress', 'closed'];

const RAW_SEVERITY_WEIGHT = { S1: 0, S2: 1, S3: 2, S4: 3 };
const UI_SEVERITY_WEIGHT = { critical: 0, warning: 1, info: 2 };
const AGING_WEIGHT = { overdue: 0, aging: 1, new: 2 };

function parseTime(value) {
  const timestamp = new Date(value || 0).getTime();
  return Number.isNaN(timestamp) ? null : timestamp;
}

/** @param {IncidentLike} item */
function incidentAgeMinutes(item) {
  const createdAt = parseTime(item.created_at);
  if (createdAt == null) return 0;
  return Math.max(0, Math.floor((Date.now() - createdAt) / 60000));
}

/** @param {string|number|null|undefined} value */
function titleCase(value) {
  if (!value) return '—';
  const text = String(value).replaceAll('_', ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** @param {string|null|undefined} name */
function initials(name) {
  return (name || '—')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('');
}

function stableFingerprint(parts) {
  return parts.map((part) => String(part || '').trim().toLowerCase()).join('|');
}

function resolveUiSeverity(incident) {
  const priority = String(incident.priority || '').toLowerCase();
  const severity = String(incident.severity || '').toUpperCase();

  if (priority === 'critical' || severity === 'S1') return 'critical';
  if (priority === 'high' || priority === 'medium' || ['S2', 'S3'].includes(severity)) return 'warning';
  return 'info';
}

function resolveUiSeverityLabel(level) {
  if (level === 'critical') return 'Критично';
  if (level === 'warning') return 'Предупреждение';
  return 'Инфо';
}

function resolveAgingCue(incident) {
  if (String(incident.status) === 'closed') {
    return 'new';
  }

  const deadlines = [incident.acknowledge_deadline_at, incident.closure_deadline_at]
    .map(parseTime)
    .filter((value) => value != null);

  if (deadlines.some((value) => value < Date.now())) {
    return 'overdue';
  }

  if (incident.sla_at_risk) {
    return 'aging';
  }

  return 'new';
}

function resolveAgingCueLabel(level) {
  if (level === 'overdue') return 'Просрочен';
  if (level === 'aging') return 'Стареет';
  return 'Новый';
}

/** @param {IncidentViewModel} left @param {IncidentViewModel} right */
function compareBySeverityAndAge(left, right) {
  const uiSeverityDiff = (UI_SEVERITY_WEIGHT[left.uiSeverity] ?? 9) - (UI_SEVERITY_WEIGHT[right.uiSeverity] ?? 9);
  if (uiSeverityDiff !== 0) return uiSeverityDiff;

  const agingDiff = (AGING_WEIGHT[left.agingCue] ?? 9) - (AGING_WEIGHT[right.agingCue] ?? 9);
  if (agingDiff !== 0) return agingDiff;

  const severityDiff = (RAW_SEVERITY_WEIGHT[left.severity] ?? 9) - (RAW_SEVERITY_WEIGHT[right.severity] ?? 9);
  if (severityDiff !== 0) return severityDiff;

  return incidentAgeMinutes(right) - incidentAgeMinutes(left);
}

/** @param {string|number|Date|null|undefined} createdAt @param {string} range */
export function timeMatches(createdAt, range) {
  if (range === 'all') return true;
  const created = new Date(createdAt || 0);
  if (Number.isNaN(created.getTime())) return false;
  const now = Date.now();
  const diff = now - created.getTime();
  if (range === '24h') return diff <= 24 * 60 * 60 * 1000;
  if (range === '7d') return diff <= 7 * 24 * 60 * 60 * 1000;
  if (range === '30d') return diff <= 30 * 24 * 60 * 60 * 1000;
  return true;
}

/** @param {IncidentLike} incident @param {TapLike|null} tapMatch @param {VisitLike|null} sessionMatch @param {IncidentAccountability} accountability */
function buildNarrative(incident, tapMatch, sessionMatch, accountability) {
  const tapLabel = tapMatch?.display_name || incident.tap || 'непривязанном кране';
  const happened = incident.status === 'closed'
    ? 'закрыт и подтверждён системой.'
    : incident.status === 'in_progress'
      ? 'находится в работе и ждёт подтверждённого результата.'
      : 'ждёт назначения ответственного и первого действия.';

  return [
    `${titleCase(incident.type)} на ${tapLabel} ${happened}`,
    accountability.owner
      ? `Ответственный: ${accountability.owner}. Последний зафиксированный шаг: ${accountability.lastActionLabel}.`
      : 'Ответственный пока не назначен. Назначьте владельца кейса перед дальнейшим разбором.',
    tapMatch?.operations?.productStateLabel
      ? `Сейчас кран в статусе «${tapMatch.operations.productStateLabel}», ${tapMatch.operations.liveStatus?.toLowerCase?.() || 'без дополнительных сигналов'}.`
      : 'По крану не хватает подтверждённых сигналов, поэтому описание собрано из данных по инциденту, крану и визиту.',
    sessionMatch
      ? `Связанный визит #${sessionMatch.visit_id}${sessionMatch.guest_full_name ? ` для гостя ${sessionMatch.guest_full_name}` : ''}${sessionMatch.operator_status ? ` со статусом ${sessionMatch.operator_status}` : ''}.`
      : 'Связанный визит не найден. Проверьте журнал визитов и сигналы по крану.',
  ];
}

/** @param {IncidentLike} incident @param {TapLike|null} tapMatch @param {VisitLike|null} sessionMatch */
function deriveImpact(incident, tapMatch, sessionMatch) {
  const impact = [];
  if (incident.priority === 'critical') impact.push('есть риск остановки продаж или несанкционированного пролива');
  if (incident.priority === 'high') impact.push('требует быстрого вмешательства смены');
  if (tapMatch?.operations?.currentPour?.isActive) impact.push('по крану прямо сейчас фиксируется поток');
  if (tapMatch?.operations?.heartbeat?.isStale) impact.push('последний сигнал от крана устарел');
  if (sessionMatch?.has_incident || sessionMatch?.incident_count) impact.push(`в истории визита уже есть инцидент (${sessionMatch.incident_count || 1})`);
  if (impact.length === 0) impact.push('локальное влияние пока ограничено и требует подтверждения оператором');
  return impact;
}

function dedupeRelatedEvents(events) {
  const byFingerprint = new Map();

  for (const event of events) {
    const fingerprint = event.dedupeFingerprint || stableFingerprint([event.title, event.description, event.time, event.label]);
    if (!byFingerprint.has(fingerprint)) {
      byFingerprint.set(fingerprint, { ...event, duplicateCount: 1 });
      continue;
    }

    const existing = byFingerprint.get(fingerprint);
    byFingerprint.set(fingerprint, {
      ...existing,
      duplicateCount: (existing.duplicateCount || 1) + 1,
      description: existing.description,
    });
  }

  return Array.from(byFingerprint.values()).map((event) => (
    event.duplicateCount > 1
      ? { ...event, description: `${event.description} Повторилось ${event.duplicateCount} раза.` }
      : event
  ));
}

/** @param {IncidentLike} incident @param {TapLike|null} tapMatch @param {VisitLike|null} sessionMatch @param {{openTap:string, openSystem:string}} incidentCopy */
function deriveRelatedEvents(incident, tapMatch, sessionMatch, incidentCopy) {
  const events = [];

  for (const item of tapMatch?.operations?.operatorHistory || []) {
    events.push({
      id: `tap-${item.id}`,
      time: item.happenedAt,
      title: item.title,
      description: item.description,
      href: item.sessionAction?.href || '#/taps',
      label: item.sessionAction?.label || incidentCopy.openTap,
      dedupeFingerprint: stableFingerprint([item.title, item.description, item.happenedAt, item.sessionAction?.visitId || item.sessionAction?.href]),
    });
  }

  if (sessionMatch) {
    events.push({
      id: `visit-${sessionMatch.visit_id}`,
      time: sessionMatch.last_event_at || sessionMatch.opened_at,
      title: `Визит #${sessionMatch.visit_id}`,
      description: `${sessionMatch.operator_status || 'Статус неизвестен'} · краны: ${sessionMatch.taps?.join(', ') || '—'}`,
      href: '#/visits',
      label: 'Открыть визит',
      dedupeFingerprint: stableFingerprint([sessionMatch.visit_id, sessionMatch.operator_status, sessionMatch.last_event_at || sessionMatch.opened_at]),
    });
  }

  if (!events.length) {
    events.push({
      id: `incident-${incident.incident_id}`,
      time: incident.created_at,
      title: 'Инцидент зарегистрирован',
      description: 'Пока доступны только сводные данные системы по этому инциденту.',
      href: '#/system',
      label: incidentCopy.openSystem,
      dedupeFingerprint: stableFingerprint([incident.incident_id, incident.created_at, incident.type, incident.source]),
    });
  }

  return dedupeRelatedEvents(events).slice(0, 6);
}

/** @param {IncidentLike} incident @param {VisitLike|null} sessionMatch @returns {IncidentAccountability} */
function deriveAccountability(incident, sessionMatch) {
  const owner = incident.owner || incident.operator || sessionMatch?.operator_name || null;
  const lastEscalatedAt = incident.escalated_at || (incident.source === 'system_state' ? incident.created_at : null);
  const lastActionLabel = incident.last_action || incident.note_action || (incident.status === 'closed' ? 'Закрытие подтверждено системой' : 'Действие ещё не зафиксировано');
  const nextStep = incident.status === 'new'
    ? 'Назначить ответственного и перевести инцидент в работу.'
    : incident.status === 'in_progress'
      ? 'Зафиксировать действие, при необходимости эскалировать и закрывать только после подтверждения системы.'
      : 'Проверить, что итог и таймлайн закрытия понятны для следующей смены.';

  return {
    owner,
    ownerLabel: owner || 'Не назначен',
    ownerBadge: owner ? `Ответственный: ${owner}` : 'Ответственный не назначен',
    ownerState: owner ? 'assigned' : 'unassigned',
    acknowledgedAt: incident.last_action_at || (incident.status !== 'new' ? incident.created_at : null) || null,
    lastEscalatedAt: lastEscalatedAt || null,
    closedAt: incident.closed_at || (incident.status === 'closed' ? incident.created_at : null) || null,
    lastActionLabel,
    nextStep,
    stateFlow: [
      {
        key: 'new',
        label: 'Новый',
        description: 'Инцидент поступил из системы и ждёт первичного разбора.',
        active: incident.status === 'new',
        done: incident.status !== 'new',
      },
      {
        key: 'in_progress',
        label: 'В работе',
        description: owner
          ? `Разбор ведёт ${owner}.`
          : 'Нужно назначить ответственного, чтобы зафиксировать работу по инциденту.',
        active: incident.status === 'in_progress',
        done: incident.status === 'closed',
      },
      {
        key: 'closed',
        label: 'Закрыт',
        description: incident.status === 'closed'
          ? 'Система уже подтвердила закрытие и считает кейс завершённым.'
          : 'Закрывать инцидент можно только после подтверждения системы.',
        active: incident.status === 'closed',
        done: incident.status === 'closed',
      },
    ],
  };
}

/** @param {IncidentLike} incident @param {TapLike|null} tapMatch @param {VisitLike|null} sessionMatch @param {IncidentAccountability} accountability */
function deriveActionsTaken(incident, tapMatch, sessionMatch, accountability) {
  const actions = [];

  if (accountability.owner) {
    actions.push({
      kind: 'owner',
      title: `Ответственный: ${accountability.owner}`,
      detail: accountability.lastActionLabel,
      time: accountability.acknowledgedAt,
    });
  }

  if (accountability.lastEscalatedAt) {
    actions.push({
      kind: 'escalation',
      title: 'Кейс передан дальше',
      detail: 'Эскалация зафиксирована как системный сигнал и требует подтверждённого следующего шага.',
      time: accountability.lastEscalatedAt,
    });
  }

  if (incident.note_action || incident.last_action) {
    actions.push({
      kind: 'note',
      title: 'Последнее подтверждённое действие',
      detail: incident.note_action || incident.last_action,
      time: incident.last_action_at || incident.created_at,
    });
  }

  if (tapMatch?.operations?.heartbeat?.isStale) {
    actions.push({
      kind: 'signal',
      title: 'Системный сигнал',
      detail: `Последний сигнал от крана был ${tapMatch.operations.heartbeat.minutesAgo} мин. назад.`,
      time: tapMatch.operations.heartbeat.at,
    });
  }

  if (sessionMatch?.incident_count) {
    actions.push({
      kind: 'history',
      title: 'След в истории визита',
      detail: `В связанном визите уже отмечен инцидент: ${sessionMatch.incident_count}.`,
      time: sessionMatch.last_event_at || sessionMatch.opened_at,
    });
  }

  return actions;
}

/** @param {IncidentLike} incident @param {TapLike|null} tapMatch @param {VisitLike[]} activeVisits */
function matchSession(incident, tapMatch, activeVisits) {
  return (activeVisits || []).find((visit) => {
    const tapIds = visit.taps || [];
    const incidentTapId = tapMatch?.tap_id;
    return (incidentTapId && (visit.active_tap_id === incidentTapId || tapIds.includes(String(incidentTapId)) || tapIds.includes(incidentTapId)))
      || (incident.tap && tapIds.includes(incident.tap));
  }) || null;
}

function uniqueIncidents(incidents = []) {
  const byId = new Map();
  for (const incident of incidents || []) {
    if (!byId.has(String(incident.incident_id))) {
      byId.set(String(incident.incident_id), incident);
    }
  }
  return Array.from(byId.values());
}

/**
 * @param {{ incidents: IncidentLike[], taps: TapLike[], activeVisits: VisitLike[], systemState: string, openIncidentCount: number, incidentCopy: {openTap:string, openSystem:string}, priorityLabels: Record<string,string>, statusLabels: Record<string,string> }} input
 * @returns {IncidentViewModel[]}
 */
export function buildEnrichedIncidents({ incidents, taps, activeVisits, systemState, openIncidentCount, incidentCopy, priorityLabels, statusLabels }) {
  return uniqueIncidents(incidents).map((incident) => {
    const tapMatch = (taps || []).find((tap) => String(tap.tap_id) === String(incident.tap) || tap.display_name === incident.tap) || null;
    const sessionMatch = matchSession(incident, tapMatch, activeVisits);
    const accountability = deriveAccountability(incident, sessionMatch);
    const tapLabel = tapMatch?.display_name || incident.tap || '—';
    const uiSeverity = resolveUiSeverity(incident);
    const agingCue = resolveAgingCue(incident);
    const requiresAction = String(incident.status) !== 'closed';

    return {
      ...incident,
      tapLabel,
      tapId: tapMatch?.tap_id || null,
      tapHref: tapMatch ? '#/taps' : null,
      sessionMatch,
      sessionHref: '#/visits',
      systemHref: '#/system',
      sourceLabel: incident.source || tapMatch?.operations?.controllerStatus?.label || 'система инцидентов',
      typeLabel: titleCase(incident.type),
      priorityLabel: priorityLabels[String(incident.priority)] || titleCase(incident.priority),
      statusLabel: statusLabels[String(incident.status)] || titleCase(incident.status),
      operatorInitials: initials(accountability.owner),
      incidentAgeMinutes: incidentAgeMinutes(incident),
      isSlaAtRisk: Boolean(incident.sla_at_risk),
      uiSeverity,
      uiSeverityLabel: resolveUiSeverityLabel(uiSeverity),
      agingCue,
      agingCueLabel: resolveAgingCueLabel(agingCue),
      requiresAction,
      entryKind: requiresAction ? 'incident' : 'event',
      accountability,
      summary: buildNarrative(incident, tapMatch, sessionMatch, accountability)[0],
      narrative: buildNarrative(incident, tapMatch, sessionMatch, accountability),
      impact: deriveImpact(incident, tapMatch, sessionMatch),
      relatedEvents: deriveRelatedEvents(incident, tapMatch, sessionMatch, incidentCopy),
      actionsTaken: deriveActionsTaken(incident, tapMatch, sessionMatch, accountability),
      tapContext: tapMatch,
      systemState,
      openIncidentCount,
      backendStatusIsAuthoritative: true,
      dedupeFingerprint: stableFingerprint([
        incident.type,
        tapLabel,
        incident.source,
        incident.priority,
        incident.severity,
        incident.status,
        incident.created_at,
      ]),
    };
  });
}

/** @param {IncidentViewModel[]} enrichedItems */
export function buildFilterOptions(enrichedItems) {
  return {
    priorities: Array.from(new Set(enrichedItems.map((item) => item.priority))).filter(Boolean),
    statuses: Array.from(new Set(enrichedItems.map((item) => item.status))).filter(Boolean),
    types: Array.from(new Set(enrichedItems.map((item) => item.type))).filter(Boolean),
    taps: Array.from(new Set(enrichedItems.map((item) => item.tapLabel))).filter(Boolean),
  };
}

/** @param {IncidentViewModel[]} enrichedItems @param {{priority:string,status:string,type:string,tap:string,time:string,query:string,slaRisk:string}} filters */
export function filterIncidents(enrichedItems, filters) {
  return enrichedItems.filter((item) => {
    const query = filters.query.trim().toLowerCase();
    return (filters.priority === 'all' || item.priority === filters.priority)
      && (filters.status === 'all' || item.status === filters.status)
      && (filters.type === 'all' || item.type === filters.type)
      && (filters.tap === 'all' || item.tapLabel === filters.tap)
      && timeMatches(item.created_at, filters.time)
      && (filters.slaRisk !== 'at_risk' || item.agingCue !== 'new')
      && (!query || [
        item.incident_id,
        item.typeLabel,
        item.tapLabel,
        item.accountability.ownerLabel,
        item.summary,
        item.uiSeverityLabel,
        item.agingCueLabel,
      ].join(' ').toLowerCase().includes(query));
  });
}

/** @param {IncidentViewModel[]} filteredItems @param {Record<string,string>} sectionLabels */
export function groupIncidentsByStatus(filteredItems, sectionLabels) {
  return SECTION_ORDER.map((status) => ({
    key: status,
    label: sectionLabels[status],
    items: filteredItems.filter((item) => item.status === status).sort(compareBySeverityAndAge),
  }));
}
