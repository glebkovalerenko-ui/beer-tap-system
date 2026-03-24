import { ACTION_LABELS, getActionPlan } from '../actionRouting.js';
import { formatVolumeRu } from '../formatters.js';

const DEFAULT_SEVERITY_WEIGHT = { critical: 0, warning: 1, info: 2 };
const DEFAULT_INCIDENT_WEIGHT = { critical: 0, high: 1, medium: 2, low: 3 };

export function sortCriticalIncidents(items, incidentPriorityWeight = DEFAULT_INCIDENT_WEIGHT) {
  return (items || [])
    .filter((item) => item.status !== 'closed')
    .filter((item) => ['critical', 'high'].includes(item.priority))
    .sort((left, right) => (incidentPriorityWeight[left.priority] ?? 9) - (incidentPriorityWeight[right.priority] ?? 9));
}

export function actionLabelForTarget(target, kind = 'default') {
  const plan = getActionPlan(kind);
  if (target === 'system' && plan.primaryCta === ACTION_LABELS.checkSync) {
    return ACTION_LABELS.checkSync;
  }
  return ACTION_LABELS[target] || ACTION_LABELS.context;
}

export function buildActionItem(item) {
  const plan = getActionPlan(item.kind || (item.target === 'incident' ? 'incident' : 'default'));
  const target = item.target || plan.primaryTarget || 'system';
  return {
    ...item,
    target,
    actionLabel: item.actionLabel || actionLabelForTarget(target, item.kind),
    secondaryCta: item.secondaryCta || plan.secondaryCta,
    recommendedOwnerState: item.recommendedOwnerState || plan.recommendedOwnerState,
    recommendedActionState: item.recommendedActionState || plan.recommendedActionState,
  };
}

export function describeSyncProblems({ tapSummary, systemHealth }) {
  return (tapSummary?.unsyncedFlowCount || 0)
    + (tapSummary?.readerOfflineCount || 0)
    + (tapSummary?.displayOfflineCount || 0)
    + (tapSummary?.controllerOfflineCount || 0)
    + (systemHealth?.sections?.accumulatedIssues?.deviceCount || 0)
    + (['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(systemHealth?.sync?.state) ? 1 : 0);
}

function attentionCategory(item) {
  const labels = {
    no_keg: 'кега',
    stale_heartbeat: 'связь с краном',
    unsynced_flow: 'синхронизация налива',
    reader_offline: 'считыватель',
    display_offline: 'экран крана',
    controller_offline: 'контроллер',
    backend_offline: 'бэкенд',
    sync_offline: 'синхронизация',
    controllers_offline: 'контроллеры',
    displays_offline: 'экраны',
    readers_offline: 'считыватели',
  };

  return labels[item.kind] || String(item.kind || 'операции').replaceAll('_', ' ');
}

function actionTitleForAttention(item) {
  const tapLabel = item.title || 'кран';

  switch (item.kind) {
    case 'unsynced_flow':
      return `Проверить зависший налив на ${tapLabel}`;
    case 'stale_heartbeat':
      return `Проверить связь с ${tapLabel}`;
    case 'reader_offline':
      return `Проверить считыватель на ${tapLabel}`;
    case 'display_offline':
      return `Проверить экран на ${tapLabel}`;
    case 'controller_offline':
      return `Проверить контроллер на ${tapLabel}`;
    case 'no_keg':
      return `Назначить кегу для ${tapLabel}`;
    default:
      return `Проверить ${tapLabel}`;
  }
}

export function buildTodayRouteModel({
  incidents,
  tapSummary,
  taps,
  systemHealth,
  todaySummary,
  todaySummaryError,
  permissions,
  dismissedAttentionKeys,
}) {
  const severityWeight = DEFAULT_SEVERITY_WEIGHT;
  const criticalIncidents = sortCriticalIncidents(incidents);
  const sessionsToday = Number(todaySummary?.sessions_count || 0);
  const volumeTodayMl = Number(todaySummary?.volume_ml || 0);
  const revenueToday = Number(todaySummary?.revenue || 0);
  const todaySummaryWarning = todaySummaryError
    || todaySummary?.fallback_copy
    || (!todaySummary?.summary_complete ? 'Сводка KPI неполная. Проверьте backend/смену перед принятием операционных решений.' : null);

  const syncProblemCount = describeSyncProblems({ tapSummary, systemHealth });
  const needsHelpCount = (taps || []).filter((tap) => tap.operations?.productState === 'needs_help').length;

  const systemAttentionItems = (systemHealth?.primaryPills || [])
    .filter((item) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(item.state))
    .map((item) => ({
      key: `system-${item.key}`,
      kind: `${item.key}_offline`,
      severity: item.state === 'critical' || item.state === 'error' ? 'critical' : 'warning',
      title: item.label,
      description: item.detail,
      href: '/system',
      target: 'system',
      systemSource: item.label,
      actionLabel: actionLabelForTarget('system'),
      category: 'система',
    }));

  const tapAttentionItems = (tapSummary?.attentionItems || []).map((item) => buildActionItem({
    ...item,
    target: item.href === '#/sessions' ? 'session' : 'tap',
    tapId: item.tapId || item.tap_id || Number.parseInt(String(item.key).split('-').at(-1), 10) || null,
    visitId: item.visitId || item.visit_id || null,
    category: attentionCategory(item),
    actionTitle: actionTitleForAttention(item),
    href: item.href?.replace('#', '') || '/taps',
  }));

  const attentionItems = [...tapAttentionItems, ...systemAttentionItems.map((item) => buildActionItem(item))]
    .filter((item) => !dismissedAttentionKeys.has(item.key))
    .sort((left, right) => (severityWeight[left.severity] ?? 9) - (severityWeight[right.severity] ?? 9));

  const operatorActionItems = [
    ...(permissions?.incidents_view ? criticalIncidents.slice(0, 3).map((incident) => buildActionItem({
      key: `incident-${incident.incident_id}`,
      severity: incident.priority === 'critical' ? 'critical' : 'warning',
      title: `Разобрать ${incident.priority === 'critical' ? 'критичный' : 'срочный'} инцидент #${incident.incident_id}`,
      description: permissions?.incidents_manage
        ? (incident.tap ? `Проверьте ${incident.tap} и зафиксируйте действие по инциденту.` : 'Откройте инцидент, назначьте ответственного и выберите решение.')
        : (incident.tap ? `Проверьте ${incident.tap}, сверяйте связанную сессию и передайте кейс дальше по маршруту смены.` : 'Откройте инцидент, посмотрите контекст и эскалируйте кейс дальше по регламенту.'),
      target: 'incident',
      tapId: incident.tap || null,
      systemSource: `Инцидент #${incident.incident_id}`,
      href: '/incidents',
    })) : []),
    ...attentionItems.slice(0, 4).map((item) => buildActionItem({
      key: `next-${item.key}`,
      severity: item.severity,
      title: item.actionTitle || `Проверить ${item.title}`,
      description: item.description,
      target: item.target,
      tapId: item.tapId || null,
      visitId: item.visitId || null,
      systemSource: item.systemSource || item.title,
      href: item.href,
    })),
  ]
    .sort((left, right) => (severityWeight[left.severity] ?? 9) - (severityWeight[right.severity] ?? 9))
    .filter((item, index, items) => items.findIndex((candidate) => candidate.key === item.key) === index)
    .slice(0, 5);

  const primaryActionItem = operatorActionItems[0] || null;
  const priorityCta = primaryActionItem
    ? {
      label: primaryActionItem.actionLabel,
      target: primaryActionItem.target,
      tapId: primaryActionItem.tapId || null,
      visitId: primaryActionItem.visitId || null,
      systemSource: primaryActionItem.systemSource || primaryActionItem.title,
      href: primaryActionItem.href,
    }
    : { label: 'Открыть систему', target: 'system', systemSource: 'Today overview', href: '/system' };

  const hasCriticalTapAttention = attentionItems.some((item) => item.target === 'tap' && item.severity === 'critical');
  const hasCriticalIncident = criticalIncidents.length > 0;
  const deEmphasizeSecondaryStats = hasCriticalIncident || hasCriticalTapAttention;
  const heroStats = [
    { label: 'Льют сейчас', value: tapSummary?.pouringCount || 0, tone: 'neutral', emphasis: 'primary' },
    { label: 'Требуют помощи', value: needsHelpCount, tone: needsHelpCount ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Открытые инциденты', value: (incidents || []).filter((item) => item.status !== 'closed').length, tone: (incidents || []).some((item) => item.status !== 'closed') ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Sync / offline', value: syncProblemCount, tone: syncProblemCount ? 'warning' : 'neutral', emphasis: 'primary' },
    { label: 'Сессии сегодня', value: sessionsToday, tone: 'neutral', emphasis: 'secondary' },
    { label: 'Объём / выручка', value: `${formatVolumeRu(volumeTodayMl)} · ${revenueToday.toFixed(2)} ₽`, tone: 'neutral', emphasis: 'secondary' },
  ];

  return {
    criticalIncidents,
    todaySummaryWarning,
    syncProblemCount,
    needsHelpCount,
    attentionItems,
    operatorActionItems,
    primaryActionItem,
    priorityCta,
    deEmphasizeSecondaryStats,
    heroStats,
  };
}
