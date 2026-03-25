<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';

  import { formatDateTimeRu } from '../../lib/formatters.js';
  import { operatorConnectionStore } from '../../stores/operatorConnectionStore.js';
  import { sessionsStore } from '../../stores/sessionsStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import DataFreshnessChip from '../common/DataFreshnessChip.svelte';
  import SessionHistoryDetailDrawer from './SessionHistoryDetailDrawer.svelte';
  import SessionHistoryFiltersPanel from './SessionHistoryFiltersPanel.svelte';
  import SessionHistoryJournal from './SessionHistoryJournal.svelte';
  import {
    completionSourceLabels,
    describeCompletionSource,
    describeCompletionSourceDetails,
    describeFlags,
    isZeroVolumeAbort,
    normalizeVisit,
  } from './sessionNormalize.js';
  import {
    buildDisplayContext,
    buildWhatHappened,
    groupedNarrative,
    normalizedOperatorActions,
    syncLabels,
  } from './sessionNarrative.js';
  import { buildOperatorActionRequest } from '../../lib/operator/actionDialogModel.js';
  import { resolveActionBlockState } from '../../lib/operator/actionPolicyAdapter.js';
  import { operatorActionStore } from '../../stores/operatorActionStore.js';

  const DEFAULT_FILTERS = {
    periodPreset: 'today',
    dateFrom: '',
    dateTo: '',
    tapId: '',
    status: '',
    cardUid: '',
    completionSource: '',
    incidentOnly: false,
    unsyncedOnly: false,
    zeroVolumeAbortOnly: false,
    activeOnly: false,
  };

  const narrativeKindLabels = {
    open: 'Визит открыт',
    authorize: 'Карта подтверждена',
    pour_start: 'Налив начался',
    pour_end: 'Налив завершён',
    sync: 'Статус синхронизации обновлён',
    close: 'Визит закрыт',
    abort: 'Визит прерван',
    incident: 'Зафиксирован инцидент',
    action: 'Действие оператора',
  };

  let filters = { ...DEFAULT_FILTERS };
  let focusVisitId = '';
  let focusTapId = '';
  let focusResolved = false;
  let selectedVisitId = '';

  $: header = $sessionsStore.header || null;
  $: pinnedActiveItems = ($sessionsStore.pinnedActiveSessions || []).map((item) => normalizeVisit(item, 'active'));
  $: journalItems = ($sessionsStore.items || []).map((item) => normalizeVisit(item, item.is_active ? 'active' : 'history'));
  $: detail = $sessionsStore.detail;
  $: focusContextText = focusVisitId
    ? `Открываем визит ${focusVisitId} в общем журнале.`
    : focusTapId
      ? `Журнал сфокусирован на кране ${focusTapId}.`
      : '';
  $: detailNarrativeGroups = detail ? groupedNarrative(detail, formatMaybeDate, describeCompletionSource) : { timeline: [], operatorObservations: [], lifecycleCards: [] };
  $: detailDisplayContext = detail ? buildDisplayContext(detail) : null;
  $: detailOperatorActions = detail ? normalizedOperatorActions(detail.summary, describeCompletionSource, describeFlags) : [];
  $: detailWhatHappened = detail ? buildWhatHappened(detail.summary, describeCompletionSource) : [];
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Backend временно деградирован. Рискованные действия по визитам доступны только для просмотра.')
    : '';
  $: if (focusVisitId && !focusResolved && !$sessionsStore.loading && !$sessionsStore.detailLoading) {
    resolveFocusVisit();
  }

  onMount(async () => {
    filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };

    const presetCardUid = sessionStorage.getItem('sessions.history.cardUid');
    if (presetCardUid) {
      sessionStorage.removeItem('sessions.history.cardUid');
      filters = { ...filters, cardUid: presetCardUid };
    }

    const presetTapId = sessionStorage.getItem('sessions.history.tapId');
    if (presetTapId) {
      sessionStorage.removeItem('sessions.history.tapId');
      focusTapId = presetTapId;
      filters = { ...filters, tapId: presetTapId };
    }

    const presetVisitId = sessionStorage.getItem('visits.lookupVisitId') || sessionStorage.getItem('sessions.history.visitId');
    if (presetVisitId) {
      sessionStorage.removeItem('visits.lookupVisitId');
      sessionStorage.removeItem('sessions.history.visitId');
      focusVisitId = presetVisitId;
    }

    await applyFilters();
  });

  function isoDateLocal(value) {
    const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  function getPeriodBounds(periodPreset) {
    const now = new Date();
    if (periodPreset === 'range') {
      return { dateFrom: filters.dateFrom, dateTo: filters.dateTo };
    }
    if (periodPreset === 'shift') {
      const shift = get(shiftStore).shift;
      if (shift?.opened_at) {
        const openedAt = new Date(shift.opened_at);
        return {
          dateFrom: isoDateLocal(openedAt),
          dateTo: shift.closed_at ? isoDateLocal(new Date(shift.closed_at)) : isoDateLocal(now),
        };
      }
    }
    const today = isoDateLocal(now);
    return { dateFrom: today, dateTo: today };
  }

  function formatMaybeDate(value) {
    return value ? formatDateTimeRu(value) : '-';
  }

  async function applyFilters() {
    focusResolved = false;
    if (filters.periodPreset !== 'range') {
      filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };
    }
    await sessionsStore.fetchJournal(filters, { force: true }).catch(() => {});
  }

  function resetFilters() {
    filters = { ...DEFAULT_FILTERS, ...getPeriodBounds(DEFAULT_FILTERS.periodPreset) };
    focusTapId = '';
    focusVisitId = '';
    focusResolved = false;
    closeDetail();
    applyFilters();
  }

  async function resolveFocusVisit() {
    const target = [...pinnedActiveItems, ...journalItems].find((item) => String(item.visit_id) === String(focusVisitId));
    if (target) {
      focusResolved = true;
      await openDetail(target);
      return;
    }
    focusResolved = true;
    selectedVisitId = String(focusVisitId);
    await sessionsStore.fetchDetail(focusVisitId).catch(() => {});
  }

  async function openDetail(item) {
    focusVisitId = String(item.visit_id);
    selectedVisitId = String(item.visit_id);
    focusResolved = true;
    await sessionsStore.fetchDetail(item.visit_id).catch(() => {});
  }

  function closeDetail() {
    selectedVisitId = '';
    sessionsStore.clearDetail();
  }

  function updatePeriodPreset(periodPreset) {
    filters = { ...filters, periodPreset, ...getPeriodBounds(periodPreset) };
  }

  function actionDisabledReason(policy) {
    return resolveActionBlockState(policy, routeReadOnlyReason).reason;
  }

  async function requestAction(actionKey, policy, context = {}) {
    const request = buildOperatorActionRequest({
      actionKey,
      policy,
      context,
      readOnlyReason: routeReadOnlyReason,
    });

    if (request.blockedReason) {
      uiStore.notifyWarning(request.blockedReason);
      return null;
    }

    return operatorActionStore.open(request);
  }

  async function handleCloseSession() {
    const policy = detail?.safe_actions?.close;
    const submission = await requestAction('session.close', policy, { visitId: detail?.summary?.visit_id });
    if (!submission) return;

    const closedReason = submission.values.reasonCode || 'incident-response';

    await sessionsStore.closeSession({ visitId: detail.summary.visit_id, closedReason, cardReturned: true });
    uiStore.notifySuccess('Визит закрыт.');
  }

  async function handleForceUnlock() {
    const policy = detail?.safe_actions?.force_unlock;
    const submission = await requestAction('session.force_unlock', policy, { visitId: detail?.summary?.visit_id });
    if (!submission) return;

    await sessionsStore.forceUnlockSession({
      visitId: detail.summary.visit_id,
      reason: submission.values.reasonCode || 'hardware-fault',
      comment: submission.values.comment || null,
    });
    uiStore.notifySuccess('Блокировка снята.');
  }

  async function handleMarkLostCard() {
    const policy = detail?.safe_actions?.mark_lost_card;
    const submission = await requestAction('session.mark_lost_card', policy, { visitId: detail?.summary?.visit_id });
    if (!submission) return;

    await sessionsStore.markLostCard({
      visitId: detail.summary.visit_id,
      reason: submission.values.reasonCode || 'security',
      comment: submission.values.comment || null,
    });
    uiStore.notifySuccess('Карта помечена как потерянная.');
  }

  async function handleReconcile() {
    const policy = detail?.safe_actions?.reconcile;
    const submission = await requestAction('session.reconcile', policy, {
      visitId: detail?.summary?.visit_id,
      defaultTapId: detail?.summary?.taps?.[0] || '',
    });
    if (!submission) return;

    await sessionsStore.reconcileSession({
      visitId: detail.summary.visit_id,
      tapId: Number(submission.values.tapId),
      shortId: submission.values.shortId,
      volumeMl: Number(submission.values.volumeMl),
      amount: submission.values.amount,
      reason: submission.values.reasonCode || 'incident-response',
      comment: submission.values.comment || null,
    });
    uiStore.notifySuccess('Ручная сверка налива выполнена.');
  }
</script>

<div class="history-layout">
  <SessionHistoryFiltersPanel
    {filters}
    {completionSourceLabels}
    loading={$sessionsStore.loading || $sessionsStore.detailLoading}
    onRefresh={applyFilters}
    onApply={applyFilters}
    onReset={resetFilters}
    onPeriodPresetChange={updatePeriodPreset}
  />

  <div class="summary-strip">
    <div class="summary-cards">
      <article><span>Всего визитов</span><strong>{header?.total_sessions || 0}</strong></article>
      <article><span>Активные</span><strong>{header?.active_sessions || 0}</strong></article>
      <article><span>С проблемами</span><strong>{header?.incident_sessions || 0}</strong></article>
      <article><span>Без sync</span><strong>{header?.unsynced_sessions || 0}</strong></article>
      <article><span>Без налива</span><strong>{header?.zero_volume_abort_sessions || 0}</strong></article>
    </div>
    <DataFreshnessChip
      label="Visits"
      lastFetchedAt={$sessionsStore.lastFetchedAt}
      staleAfterMs={$sessionsStore.staleTtlMs}
      mode={$operatorConnectionStore.mode}
      transport={$operatorConnectionStore.transport}
      reason={$operatorConnectionStore.reason}
    />
  </div>

  {#if routeReadOnlyReason}
    <div class="degraded-banner">{routeReadOnlyReason}</div>
  {/if}

  {#if focusContextText}
    <div class="focus-banner">{focusContextText}</div>
  {/if}

  <div class="content-grid">
    <SessionHistoryJournal
      {pinnedActiveItems}
      {journalItems}
      {selectedVisitId}
      {filters}
      {syncLabels}
      {formatMaybeDate}
      {describeCompletionSourceDetails}
      {isZeroVolumeAbort}
      onOpenDetail={openDetail}
    />

    <SessionHistoryDetailDrawer
      {detail}
      {detailNarrativeGroups}
      {detailDisplayContext}
      {detailOperatorActions}
      {detailWhatHappened}
      {narrativeKindLabels}
      {formatMaybeDate}
      {syncLabels}
      actionLoading={$sessionsStore.actionLoading}
      actionError={$sessionsStore.actionError}
      readOnlyReason={routeReadOnlyReason}
      getActionDisabledReason={actionDisabledReason}
      onCloseSession={handleCloseSession}
      onForceUnlock={handleForceUnlock}
      onReconcileSession={handleReconcile}
      onMarkLostCard={handleMarkLostCard}
      onCloseDetail={closeDetail}
    />
  </div>
</div>

<style>
  .history-layout { display: grid; gap: 1rem; }
  .content-grid { display: grid; grid-template-columns: minmax(320px, 1.2fr) minmax(380px, 0.9fr); gap: 1rem; align-items: start; }
  .summary-strip { display: flex; justify-content: space-between; gap: 1rem; align-items: start; flex-wrap: wrap; }
  .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem; flex: 1 1 520px; }
  .summary-cards article,
  .focus-banner,
  .degraded-banner { border: 1px solid var(--state-neutral-border); border-radius: 12px; padding: 0.85rem 1rem; }
  .summary-cards article { background: #fff; display: grid; gap: 0.25rem; }
  .summary-cards article span { color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  .degraded-banner { background: var(--state-warning-bg, #fff7ed); border-color: var(--state-warning-border, #fcd34d); color: var(--state-warning-text, #9a3412); }
  .focus-banner { color: var(--state-neutral-text); background: var(--state-neutral-bg); }

  :global(.filters-panel),
  :global(.list-panel),
  :global(.drawer),
  :global(.timeline-section),
  :global(.summary-section),
  :global(.list-stack) { display: grid; gap: 1rem; }

  :global(.filters-title),
  :global(.actions),
  :global(.list-head),
  :global(.drawer-head),
  :global(.row),
  :global(.timeline li),
  :global(dl div),
  :global(.stats-grid) { display: flex; gap: 0.75rem; }

  :global(.filters-title),
  :global(.actions),
  :global(.list-head),
  :global(.drawer-head),
  :global(.row),
  :global(.timeline li),
  :global(dl div) { justify-content: space-between; }

  :global(.filters-grid) { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 0.75rem; }
  :global(.period-grid) { align-items: end; }
  :global(label) { display: grid; gap: 0.35rem; font-size: 0.92rem; }
  :global(input), :global(select), :global(button), :global(textarea) { font: inherit; }
  :global(input), :global(select), :global(textarea) { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; }
  :global(.checkbox) { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  :global(.session-list), :global(.timeline) { display: grid; gap: 0.75rem; }
  :global(.session-item), :global(.actions button), :global(.drawer-head button), :global(.filters-title button) { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.9rem; text-align: left; }
  :global(.session-item) { transition: border-color 0.15s ease, box-shadow 0.15s ease; }
  :global(.session-item:hover), :global(.session-item.selected) { border-color: #2563eb; box-shadow: 0 0 0 1px #bfdbfe; }
  :global(.session-item.pinned) { background: linear-gradient(180deg, #f8fbff 0%, #eff6ff 100%); }
  :global(.chips) { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.5rem; }
  :global(.chips span), :global(.eyebrow), :global(.muted), :global(small), :global(dt) { color: var(--text-secondary, #64748b); }
  :global(.chips span) { background: #f1f5f9; border-radius: 999px; padding: 0.2rem 0.55rem; }
  :global(.chips span[data-tone='warning']) { background: var(--state-warning-bg); color: var(--state-warning-text); }
  :global(.chips span[data-tone='info']) { background: var(--state-neutral-bg); color: var(--state-neutral-text); }
  :global(.chips span[data-tone='muted']) { background: #f8fafc; color: #475569; }
  :global(.meta-grid) { flex-wrap: wrap; }
  :global(.completion-pill) { font-weight: 600; color: #0f172a; }
  :global(.drawer) { position: sticky; top: 0; min-height: 320px; max-height: 85vh; overflow: auto; }
  :global(.drawer-open) { border-color: var(--state-neutral-border); }
  :global(.stats-grid) { flex-wrap: wrap; }
  :global(.stats-grid article), :global(.summary-section), :global(.empty-drawer) { border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.85rem; }
  :global(.stats-grid article) { flex: 1 1 180px; display: grid; gap: 0.35rem; }
  :global(.timeline) { list-style: none; padding: 0; margin: 0; }
  :global(.timeline li) { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  :global(.timeline p), :global(.drawer-head h2), :global(.drawer-head p), :global(.list-head h3), :global(.list-head p), :global(.summary-section p), :global(.filters-title h2), :global(.filters-title p), :global(.empty-drawer h2), :global(.empty-drawer p), :global(.nested-summary strong) { margin: 0; }
  :global(.time) { min-width: 132px; color: var(--text-secondary, #64748b); font-size: 0.85rem; }
  :global(.counter), :global(.state) { border-radius: 999px; padding: 0.2rem 0.65rem; background: #f1f5f9; color: #475569; }
  :global(.state.active) { background: var(--state-success-bg); color: var(--state-success-text); }
  :global(dl) { display: grid; gap: 0.5rem; margin: 0; }
  :global(.display-context-grid) { grid-template-columns: 1fr; }
  :global(.override-list) { margin: 0; padding-left: 1.2rem; display: grid; gap: 0.35rem; }
  :global(.nested-summary) { gap: 0.65rem; }
  :global(.compact-list) { gap: 0.5rem; }

  @media (max-width: 1100px) {
    .content-grid { grid-template-columns: 1fr; }
    :global(.filters-grid) { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    :global(.drawer) { position: static; max-height: none; }
  }
</style>
