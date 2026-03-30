<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';

  import { navigateWithFocus } from '../../lib/actionRouting.js';
  import { normalizeError } from '../../lib/errorUtils.js';
  import { formatDateTimeRu, formatRubAmount } from '../../lib/formatters.js';
  import { buildOperatorActionRequest } from '../../lib/operator/actionDialogModel.js';
  import { resolveActionBlockState } from '../../lib/operator/actionPolicyAdapter.js';
  import { buildVisitLauncherCandidates, resolveVisitFocusTarget } from '../../lib/operator/visitWorkspace.js';
  import { resolveCanonicalVisitStatus } from '../../lib/operator/visitStatus.js';
  import { guestStore } from '../../stores/guestStore.js';
  import { operatorConnectionStore } from '../../stores/operatorConnectionStore.js';
  import { operatorActionStore } from '../../stores/operatorActionStore.js';
  import { ensureOperatorShellData } from '../../stores/operatorShellOrchestrator.js';
  import { sessionsStore } from '../../stores/sessionsStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import { visitStore } from '../../stores/visitStore.js';
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
  let launcherQuery = '';
  let launcherBusy = false;
  let launcherError = '';

  $: header = $sessionsStore.header || null;
  $: pinnedActiveItems = ($sessionsStore.pinnedActiveSessions || []).map((item) => normalizeVisit(item, 'active'));
  $: journalItems = ($sessionsStore.items || []).map((item) => normalizeVisit(item, item.is_active ? 'active' : 'history'));
  $: detail = $sessionsStore.detail;
  $: summaryVisits = Array.from(new Map([...pinnedActiveItems, ...journalItems].map((item) => [String(item.visit_id), item])).values());
  $: summaryCards = [
    { key: 'active', label: 'Активные', value: header?.active_sessions || 0 },
    { key: 'pouring', label: 'Льют сейчас', value: summaryVisits.filter((item) => resolveCanonicalVisitStatus(item) === 'pouring_now').length },
    { key: 'awaiting', label: 'Ожидают действия', value: summaryVisits.filter((item) => resolveCanonicalVisitStatus(item) === 'awaiting_action').length },
    { key: 'attention', label: 'Требуют внимания', value: summaryVisits.filter((item) => ['needs_attention', 'blocked'].includes(resolveCanonicalVisitStatus(item))).length },
  ];
  $: secondarySummary = [
    `Всего: ${header?.total_sessions || 0}`,
    `Завершены: ${summaryVisits.filter((item) => resolveCanonicalVisitStatus(item) === 'completed').length}`,
    `Без синхронизации: ${header?.unsynced_sessions || 0}`,
    `Без налива: ${header?.zero_volume_abort_sessions || 0}`,
  ];
  $: focusContextText = focusVisitId
    ? `Открываем визит #${focusVisitId} в журнале.`
    : focusTapId
      ? `Журнал сфокусирован на кране #${focusTapId}.`
      : '';
  $: detailNarrativeGroups = detail ? groupedNarrative(detail, formatMaybeDate, describeCompletionSource) : { timeline: [], operatorObservations: [], lifecycleCards: [] };
  $: detailDisplayContext = detail ? buildDisplayContext(detail) : null;
  $: detailOperatorActions = detail ? normalizedOperatorActions(detail.summary, describeCompletionSource, describeFlags) : [];
  $: detailWhatHappened = detail ? buildWhatHappened(detail.summary, describeCompletionSource) : [];
  $: launcherCandidates = buildVisitLauncherCandidates({
    guests: $guestStore.guests || [],
    activeVisits: $visitStore.activeVisits || [],
    query: launcherQuery,
    limit: 6,
  });
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Сервер отвечает нестабильно. Действия по визитам временно доступны только для просмотра.')
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

    const presetVisitId = sessionStorage.getItem('visits.focusVisitId')
      || sessionStorage.getItem('visits.lookupVisitId')
      || sessionStorage.getItem('sessions.history.visitId');
    if (presetVisitId) {
      sessionStorage.removeItem('visits.focusVisitId');
      sessionStorage.removeItem('visits.lookupVisitId');
      sessionStorage.removeItem('sessions.history.visitId');
      focusVisitId = presetVisitId;
    }

    await Promise.allSettled([
      applyFilters(),
      guestStore.fetchGuests({ force: ($guestStore.guests || []).length === 0 }),
      visitStore.fetchActiveVisits({ force: ($visitStore.activeVisits || []).length === 0 }),
    ]);
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
    const target = resolveVisitFocusTarget([...pinnedActiveItems, ...journalItems], focusVisitId);
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

  async function refreshVisitWorkspace({ visitId = null, refreshGuests = false } = {}) {
    const tasks = [
      sessionsStore.fetchJournal(filters, { force: true }),
      ensureOperatorShellData({ reason: 'manual-refresh', force: true }),
    ];
    if (refreshGuests) {
      tasks.push(guestStore.fetchGuests({ force: true }));
    }
    if (visitId) {
      tasks.push(sessionsStore.fetchDetail(visitId));
    }
    await Promise.allSettled(tasks);
  }

  async function handleLauncherVisit(candidate) {
    if (!candidate?.guestId || launcherBusy) return;
    launcherBusy = true;
    launcherError = '';

    try {
      if (candidate.activeVisitId) {
        await refreshVisitWorkspace({ visitId: candidate.activeVisitId });
        focusVisitId = String(candidate.activeVisitId);
        selectedVisitId = String(candidate.activeVisitId);
        focusResolved = true;
        return;
      }

      const opened = await visitStore.openVisit({ guestId: candidate.guestId });
      await refreshVisitWorkspace({ visitId: opened.visit_id, refreshGuests: true });
      focusVisitId = String(opened.visit_id);
      selectedVisitId = String(opened.visit_id);
      focusResolved = true;
      uiStore.notifySuccess('Визит открыт.');
    } catch (error) {
      launcherError = normalizeError(error);
      uiStore.notifyError(launcherError);
    } finally {
      launcherBusy = false;
    }
  }

  function openGuestContext(guestId, cardUid = null) {
    navigateWithFocus({
      target: 'guest',
      guestId,
      cardUid,
      visitId: detail?.summary?.visit_id || focusVisitId || null,
      tapId: detail?.summary?.tap_id || null,
    });
  }

  function openTapContext(tapId) {
    if (!tapId) return;
    navigateWithFocus({
      target: 'tap',
      tapId,
      visitId: detail?.summary?.visit_id || focusVisitId || null,
      cardUid: detail?.summary?.card_uid || null,
    });
  }

  function openVisitPours() {
    if (!detail?.summary?.visit_id) return;
    navigateWithFocus({
      target: 'pour',
      route: '/pours',
      visitId: detail.summary.visit_id,
      tapId: detail.summary.tap_id || null,
      guestId: detail.summary.guest_id || null,
      cardUid: detail.summary.card_uid || null,
    });
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

  <section class="ui-card visit-launcher">
    <div class="launcher-head">
      <div>
        <h2>Открыть или продолжить визит</h2>
        <p>Найдите гостя по имени, телефону или карте и откройте нужный визит прямо из рабочего экрана.</p>
      </div>
      <button class="secondary" on:click={() => { launcherQuery = ''; launcherError = ''; }}>Очистить</button>
    </div>

    <div class="launcher-bar">
      <input
        type="text"
        bind:value={launcherQuery}
        placeholder="Гость, телефон или UID карты"
      />
    </div>

    {#if launcherError}
      <p class="launcher-error">{launcherError}</p>
    {:else if launcherQuery.trim().length < 2}
      <p class="muted">Введите минимум 2 символа, чтобы быстро найти гостя и открыть визит.</p>
    {:else if launcherCandidates.length === 0}
      <p class="muted">По этому запросу гость не найден.</p>
    {:else}
      <div class="launcher-list">
        {#each launcherCandidates as candidate}
          <article class="launcher-item">
            <div class="launcher-copy">
              <strong>{candidate.fullName}</strong>
              <p>
                {candidate.phoneNumber || 'Телефон не указан'}
                · {candidate.cardUid || 'без карты'}
                · баланс {formatRubAmount(candidate.balance)}
              </p>
              <small>
                {#if candidate.activeVisitId}
                  Активный визит #{candidate.activeVisitId}{candidate.activeTapId ? ` · кран #${candidate.activeTapId}` : ''}
                {:else}
                  Активного визита сейчас нет
                {/if}
              </small>
            </div>
            <div class="launcher-actions">
              <button on:click={() => handleLauncherVisit(candidate)} disabled={launcherBusy}>
                {candidate.actionLabel}
              </button>
              <button class="secondary" on:click={() => openGuestContext(candidate.guestId, candidate.cardUid)}>
                Гость
              </button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  <div class="summary-strip">
    <div class="summary-cards">
      {#each summaryCards as item}
        <article>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </article>
      {/each}
    </div>
    <DataFreshnessChip
      label="Визиты"
      lastFetchedAt={$sessionsStore.lastFetchedAt}
      staleAfterMs={$sessionsStore.staleTtlMs}
      mode={$operatorConnectionStore.mode}
      transport={$operatorConnectionStore.transport}
      reason={$operatorConnectionStore.reason}
    />
  </div>

  <p class="summary-secondary">{secondarySummary.join(' · ')}</p>

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
      onContinueVisit={openDetail}
      onOpenGuest={(item) => openGuestContext(item.guest_id, item.card_uid)}
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
      onOpenGuest={() => openGuestContext(detail?.summary?.guest_id, detail?.summary?.card_uid)}
      onOpenTap={() => openTapContext(detail?.summary?.tap_id)}
      onOpenPours={openVisitPours}
      onCloseDetail={closeDetail}
    />
  </div>
</div>

<style>
  .history-layout { display: grid; gap: 0.85rem; }
  .content-grid { display: grid; grid-template-columns: minmax(320px, 1.2fr) minmax(380px, 0.9fr); gap: 0.9rem; align-items: start; }
  .summary-strip { display: flex; justify-content: space-between; gap: 0.75rem; align-items: start; flex-wrap: wrap; }
  .visit-launcher,
  .launcher-list { display: grid; gap: 0.75rem; }
  .launcher-head,
  .launcher-actions,
  .launcher-item { display: flex; gap: 0.75rem; justify-content: space-between; }
  .launcher-head,
  .launcher-item { align-items: flex-start; }
  .launcher-head h2,
  .launcher-head p,
  .launcher-copy p,
  .launcher-copy small { margin: 0; }
  .launcher-bar input { width: 100%; }
  .launcher-item {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    background: #fff;
    flex-wrap: wrap;
  }
  .launcher-copy { display: grid; gap: 0.2rem; }
  .launcher-copy p,
  .launcher-copy small,
  .launcher-head p,
  .launcher-error { color: var(--text-secondary, #64748b); }
  .launcher-actions { flex-wrap: wrap; }
  .launcher-error { margin: 0; color: var(--state-critical-text, #9f1239); }
  .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: 0.65rem; flex: 1 1 520px; }
  .summary-cards article,
  .focus-banner,
  .degraded-banner { border: 1px solid var(--state-neutral-border); border-radius: 12px; padding: 0.7rem 0.85rem; }
  .summary-cards article { background: #fff; display: grid; gap: 0.25rem; }
  .summary-cards article span { color: var(--text-secondary, #64748b); font-size: 0.82rem; }
  .summary-secondary { margin: 0; color: var(--text-secondary, #64748b); }
  .degraded-banner { background: var(--state-warning-bg, #fff7ed); border-color: var(--state-warning-border, #fcd34d); color: var(--state-warning-text, #9a3412); }
  .focus-banner { color: var(--state-neutral-text); background: var(--state-neutral-bg); }

  :global(.filters-panel),
  :global(.list-panel),
  :global(.drawer),
  :global(.timeline-section),
  :global(.summary-section),
  :global(.list-stack) { display: grid; gap: 0.85rem; }

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

  :global(.filters-grid) { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 0.65rem; }
  :global(.period-grid) { align-items: end; }
  :global(label) { display: grid; gap: 0.35rem; font-size: 0.92rem; }
  :global(input), :global(select), :global(button), :global(textarea) { font: inherit; }
  :global(input), :global(select), :global(textarea) { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.58rem 0.72rem; }
  :global(.checkbox) { align-self: end; display: flex; gap: 0.5rem; align-items: center; }
  :global(.session-list), :global(.timeline) { display: grid; gap: 0.75rem; }
  :global(.session-item), :global(.actions button), :global(.drawer-head button), :global(.filters-title button) { border: 1px solid #cbd5e1; border-radius: 14px; background: #fff; padding: 0.8rem; text-align: left; }
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
  :global(.drawer) { position: sticky; top: 0; min-height: 320px; max-height: 82vh; overflow: auto; }
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
    .launcher-head,
    .launcher-item { display: grid; }
    :global(.filters-grid) { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    :global(.drawer) { position: static; max-height: none; }
  }
</style>
