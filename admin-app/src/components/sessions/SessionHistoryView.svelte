<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { visitStore } from '../../stores/visitStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { formatDateTimeRu } from '../../lib/formatters.js';
  import { matchesSessionFilters } from './sessionFilters.js';
  import {
    completionSourceLabels,
    describeCompletionSource,
    describeCompletionSourceDetails,
    describeFlags,
    isZeroVolumeAbort,
    mergeVisits,
    normalizeVisit,
  } from './sessionNormalize.js';
  import {
    buildDisplayContext,
    buildWhatHappened,
    groupedNarrative,
    normalizedOperatorActions,
    syncLabels,
  } from './sessionNarrative.js';
  import SessionHistoryFiltersPanel from './SessionHistoryFiltersPanel.svelte';
  import SessionHistoryJournal from './SessionHistoryJournal.svelte';
  import SessionHistoryDetailDrawer from './SessionHistoryDetailDrawer.svelte';

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
    open: 'Сессия открыта',
    authorize: 'Карта подтверждена',
    pour_start: 'Налив начался',
    pour_end: 'Налив завершён',
    sync: 'Статус синхронизации обновлён',
    close: 'Сессия закрыта',
    abort: 'Сессия прервана',
    incident: 'Зафиксирован инцидент',
    action: 'Действие оператора',
  };

  let filters = { ...DEFAULT_FILTERS };
  let focusVisitId = '';
  let focusTapId = '';
  let focusResolved = false;
  let selectedVisitId = '';

  $: activeItems = ($visitStore.activeVisits || []).map((item) => normalizeVisit(item, 'active'));
  $: historyItems = ($visitStore.sessionHistory || []).map((item) => normalizeVisit(item, 'history'));
  $: mergedItems = mergeVisits(activeItems, historyItems);
  $: filteredItems = mergedItems.filter((item) => matchesSessionFilters(item, filters, getPeriodBounds));
  $: pinnedActiveItems = filteredItems.filter((item) => item.isActive);
  $: journalItems = filters.activeOnly ? pinnedActiveItems : filteredItems.filter((item) => !item.isActive);
  $: detail = $visitStore.sessionHistoryDetail;
  $: focusContextText = focusVisitId
    ? `Открываем сессию ${focusVisitId} в общем журнале.`
    : focusTapId
      ? `Журнал сфокусирован на кране ${focusTapId}.`
      : '';
  $: detailNarrativeGroups = detail ? groupedNarrative(detail, formatMaybeDate, describeCompletionSource) : { timeline: [], operatorObservations: [], lifecycleCards: [] };
  $: detailDisplayContext = detail ? buildDisplayContext(detail) : null;
  $: detailOperatorActions = detail ? normalizedOperatorActions(detail.summary, describeCompletionSource, describeFlags) : [];
  $: if (focusVisitId && !focusResolved && !$visitStore.historyLoading && (!$visitStore.loading || activeItems.length > 0 || historyItems.length > 0)) {
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
    return value ? formatDateTimeRu(value) : '—';
  }

  async function applyFilters() {
    focusResolved = false;
    if (filters.periodPreset !== 'range') {
      filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };
    }
    await Promise.all([
      visitStore.fetchActiveVisits().catch(() => {}),
      visitStore.fetchSessionHistory(filters).catch(() => {}),
    ]);
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
    const target = mergedItems.find((item) => String(item.visit_id) === String(focusVisitId));
    if (target) {
      focusResolved = true;
      await openDetail(target);
      return;
    }
    focusResolved = true;
    selectedVisitId = String(focusVisitId);
    await visitStore.fetchSessionHistoryDetail(focusVisitId).catch(() => {});
  }

  async function openDetail(item) {
    focusVisitId = String(item.visit_id);
    selectedVisitId = String(item.visit_id);
    focusResolved = true;
    await visitStore.fetchSessionHistoryDetail(item.visit_id).catch(() => {});
  }

  function closeDetail() {
    selectedVisitId = '';
    visitStore.clearSessionHistoryDetail();
  }

  function updatePeriodPreset(periodPreset) {
    filters = { ...filters, periodPreset, ...getPeriodBounds(periodPreset) };
  }
</script>

<div class="history-layout">
  <SessionHistoryFiltersPanel
    {filters}
    {completionSourceLabels}
    loading={$visitStore.historyLoading || $visitStore.loading}
    onRefresh={applyFilters}
    onApply={applyFilters}
    onReset={resetFilters}
    onPeriodPresetChange={updatePeriodPreset}
  />

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
      {narrativeKindLabels}
      {formatMaybeDate}
      {buildWhatHappened}
      onCloseDetail={closeDetail}
    />
  </div>
</div>

<style>
  .history-layout { display: grid; gap: 1rem; }
  .content-grid { display: grid; grid-template-columns: minmax(320px, 1.2fr) minmax(380px, 0.9fr); gap: 1rem; align-items: start; }
  .focus-banner { border: 1px solid #bfdbfe; border-radius: 12px; padding: 0.85rem 1rem; color: #1d4ed8; background: #eff6ff; }

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
  :global(input), :global(select), :global(button) { font: inherit; }
  :global(input), :global(select) { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; }
  :global(.checkbox) { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  :global(.session-list), :global(.timeline) { display: grid; gap: 0.75rem; }
  :global(.session-item), :global(.actions button), :global(.drawer-head button), :global(.filters-title button) { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.9rem; text-align: left; }
  :global(.session-item) { transition: border-color 0.15s ease, box-shadow 0.15s ease; }
  :global(.session-item:hover), :global(.session-item.selected) { border-color: #2563eb; box-shadow: 0 0 0 1px #bfdbfe; }
  :global(.session-item.pinned) { background: linear-gradient(180deg, #f8fbff 0%, #eff6ff 100%); }
  :global(.chips) { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.5rem; }
  :global(.chips span), :global(.eyebrow), :global(.muted), :global(small), :global(dt) { color: var(--text-secondary, #64748b); }
  :global(.chips span) { background: #f1f5f9; border-radius: 999px; padding: 0.2rem 0.55rem; }
  :global(.meta-grid) { flex-wrap: wrap; }
  :global(.completion-pill) { font-weight: 600; color: #0f172a; }
  :global(.drawer) { position: sticky; top: 0; min-height: 320px; max-height: 85vh; overflow: auto; }
  :global(.drawer-open) { border-color: #bfdbfe; }
  :global(.stats-grid) { flex-wrap: wrap; }
  :global(.stats-grid article), :global(.summary-section), :global(.empty-drawer) { border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.85rem; }
  :global(.stats-grid article) { flex: 1 1 180px; display: grid; gap: 0.35rem; }
  :global(.timeline) { list-style: none; padding: 0; margin: 0; }
  :global(.timeline li) { align-items: flex-start; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.75rem; }
  :global(.timeline p), :global(.drawer-head h2), :global(.drawer-head p), :global(.list-head h3), :global(.list-head p), :global(.summary-section p), :global(.filters-title h2), :global(.filters-title p), :global(.empty-drawer h2), :global(.empty-drawer p), :global(.nested-summary strong) { margin: 0; }
  :global(.time) { min-width: 132px; color: var(--text-secondary, #64748b); font-size: 0.85rem; }
  :global(.counter), :global(.state) { border-radius: 999px; padding: 0.2rem 0.65rem; background: #f1f5f9; color: #475569; }
  :global(.state.active) { background: #dcfce7; color: #166534; }
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
