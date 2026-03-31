<script>
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import { guestStore } from '../stores/guestStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { cardsGuestsWorkflowStore } from '../stores/cardsGuestsWorkflowStore.js';
  import { ensureCardsGuestsData } from '../stores/operatorShellOrchestrator.js';
  import { normalizeError } from '../lib/errorUtils.js';
  import { formatDateTimeRu, formatRubAmount } from '../lib/formatters.js';
  import { fullName, resolveLookupScenario } from '../lib/cardsGuests/scenarios/lookup.js';
  import { resolveTopUpPreconditions } from '../lib/cardsGuests/scenarios/topup.js';
  import { buildReissueHint, getReissueTargetVisitId, validateReissueInput } from '../lib/cardsGuests/scenarios/lost_reissue.js';
  import { buildOperatorActionRequest } from '../lib/operator/actionDialogModel.js';
  import { buildCardsGuestsViewModel, resolveScenarioActionHandler } from '../lib/operator/cardsGuestsModel.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';
  import { operatorActionStore } from '../stores/operatorActionStore.js';

  let phoneQuery = '';
  let lookupError = '';
  let pageError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let isManagementModalOpen = false;
  let formError = '';
  let reissueUidInput = '';
  let reissueError = '';
  let isReissueBusy = false;
  const SCENARIO_BADGE_LABELS = {
    'check-card': 'Карта проверена',
    'top-up': 'Нужно пополнение',
    'toggle-block': 'Проверьте статус карты',
    reissue: 'Нужен перевыпуск',
    'open-history': 'Откройте историю',
    'open-visit': 'Откройте активную сессию',
  };

  $: cardsGuestsWorkflowStore.setPermissions($roleStore.permissions || {});
  $: workflow = $cardsGuestsWorkflowStore;
  $: pendingScenario = workflow.pendingScenario;
  $: pendingScenarioLabel = pendingScenario ? (SCENARIO_BADGE_LABELS[pendingScenario] || 'Требуется действие') : '';
  $: selectedLookup = workflow.selectedLookup;
  $: reissueStatus = workflow.reissueStatus;
  $: selectedGuestId = workflow.selectedGuestId;

  $: canAccessCardsGuests = workflow.permissions.canAccessCardsGuests;
  $: canOpenVisit = workflow.permissions.canOpenVisit;
  $: canViewHistory = workflow.permissions.canViewHistory;
  $: canTopUp = workflow.permissions.canTopUp;
  $: canToggleBlock = workflow.permissions.canToggleBlock;
  $: canReissue = workflow.permissions.canReissue;
  $: hasManagementAccess = canToggleBlock || canReissue;
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Backend temporarily degraded. Card and guest mutations stay read-only until fresh data returns.')
    : '';

  $: guests = $guestStore.guests || [];
  $: activeVisits = $visitStore.activeVisits || [];
  $: cardsGuestsModel = buildCardsGuestsViewModel({
    guests,
    activeVisits,
    pours: $pourStore.pours,
    phoneQuery,
    selectedGuestId,
    selectedLookup,
    permissions: { canTopUp, canToggleBlock, canReissue, canOpenVisit, canViewHistory },
  });
  $: quickLookupResults = cardsGuestsModel.quickLookupResults;
  $: selectedGuest = cardsGuestsModel.selectedGuest;
  $: selectedVisit = cardsGuestsModel.selectedVisit;
  $: recentGuestPours = cardsGuestsModel.recentGuestPours;
  $: lastTapLabel = cardsGuestsModel.lastTapLabel;
  $: recentEvents = cardsGuestsModel.recentEvents;
  $: lookupGuestName = cardsGuestsModel.lookupGuestName;
  $: hasLookup = cardsGuestsModel.hasLookup;
  $: lookupSummaryItems = cardsGuestsModel.lookupSummaryItems;
  $: quickActions = cardsGuestsModel.quickActions;
  $: actionGuards = cardsGuestsModel.actionGuards || {};

  function ensureWritable() {
    if (!routeReadOnlyReason) {
      return true;
    }
    uiStore.notifyWarning(routeReadOnlyReason);
    return false;
  }

  async function requestCardAction(actionKey, guard, context = {}) {
    const request = buildOperatorActionRequest({
      actionKey,
      policy: guard,
      context,
      readOnlyReason: routeReadOnlyReason,
    });

    if (request.blockedReason) {
      uiStore.notifyWarning(request.blockedReason);
      return null;
    }

    return operatorActionStore.open(request);
  }

  function selectGuest(guestId) {
    cardsGuestsWorkflowStore.setSelectedGuestId(guestId);
    pageError = '';
    if (!pendingScenario && guestId) cardsGuestsWorkflowStore.setPendingScenario('check-card');
  }

  async function handleLookup(event) {
    lookupError = '';
    pageError = '';
    reissueError = '';
    cardsGuestsWorkflowStore.setReissueStatus('');
    try {
      const resolvedLookup = await lostCardStore.resolveCard(event.detail.uid);
      cardsGuestsWorkflowStore.setSelectedLookup(resolvedLookup);
      cardsGuestsWorkflowStore.setPendingScenario(resolveLookupScenario(resolvedLookup, canReissue));
      if (resolvedLookup?.guest?.guest_id) {
        cardsGuestsWorkflowStore.setSelectedGuestId(resolvedLookup.guest.guest_id);
      }
      await visitStore.fetchActiveVisits();
    } catch (error) {
      lookupError = normalizeError(error);
      cardsGuestsWorkflowStore.setSelectedLookup(null);
    }
  }

async function handleRestoreLost(event) {
    if (!ensureWritable()) {
      return;
    }
    const submission = await requestCardAction('card.restore_lost', actionGuards.restoreLost, { guestName: lookupGuestName });
    if (!submission) return;
    const uid = event.detail.uid;
    if (!uid) return;
    try {
      await lostCardStore.restoreLostCard(uid);
      cardsGuestsWorkflowStore.setSelectedLookup(await lostCardStore.resolveCard(uid));
      cardsGuestsWorkflowStore.setReissueStatus('Отметка lost снята. Можно привязать новую карту и перенести активную сессию.');
      uiStore.notifySuccess('Отметка lost снята');
    } catch (error) {
      lookupError = normalizeError(error);
    }
  }

  function resolveVisitAndNavigate() {
    const visitId = getReissueTargetVisitId({ selectedVisit, selectedLookup });
    if (!visitId) return false;
    sessionStorage.setItem('visits.lookupVisitId', visitId);
    window.location.hash = '/visits';
    return true;
  }

  function handleOpenVisit() {
    if (actionGuards.openVisit?.disabled) {
      uiStore.notifyWarning(actionGuards.openVisit.reason || 'Active session is unavailable.');
      return;
    }
    resolveVisitAndNavigate();
  }

  function handleOpenHistory() {
    if (actionGuards.openHistory?.disabled) {
      uiStore.notifyWarning(actionGuards.openHistory.reason || 'History is unavailable.');
      return;
    }
    const cardUid = selectedLookup?.card_uid || selectedGuest?.cards?.[0]?.card_uid || '';
    if (cardUid) sessionStorage.setItem('sessions.history.cardUid', cardUid);
    window.location.hash = '/sessions/history';
  }

  async function handleOpenNewVisit(event) {
    uiStore.notifyWarning('Открытие нового визита доступно только в flow выдачи карты на экране Visits.');
  }

  function handleOpenTopUpModal() {
    if (actionGuards.topUp?.disabled) {
      uiStore.notifyWarning(actionGuards.topUp.reason || 'Top-up is unavailable.');
      return;
    }
    const checks = resolveTopUpPreconditions({
      canTopUp,
      hasGuest: Boolean(selectedGuest),
      isShiftOpen: get(shiftStore).isOpen,
    });
    if (!checks.ok) {
      uiStore.notifyWarning(checks.message);
      return;
    }
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    if (!ensureWritable()) {
      return;
    }
    topUpError = '';
    try {
      await guestStore.topUpBalance(selectedGuest.guest_id, event.detail);
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Баланс пополнен на ${formatRubAmount(event.detail.amount)}`);
    } catch (error) {
      topUpError = normalizeError(error);
    }
  }

async function handleToggleBlock() {
    if (!ensureWritable()) {
      return;
    }
    const submission = await requestCardAction('card.toggle_block', actionGuards.toggleBlock, {
      guestName: lookupGuestName,
      isActive: Boolean(selectedGuest?.is_active),
    });
    if (!submission) return;
    if (!selectedGuest) return;
    pageError = '';
    try {
      await guestStore.updateGuest(selectedGuest.guest_id, {
        last_name: selectedGuest.last_name,
        first_name: selectedGuest.first_name,
        patronymic: selectedGuest.patronymic || '',
        phone_number: selectedGuest.phone_number,
        date_of_birth: selectedGuest.date_of_birth,
        id_document: selectedGuest.id_document,
        is_active: !selectedGuest.is_active,
      });
      uiStore.notifySuccess(selectedGuest.is_active ? 'Гость заблокирован' : 'Гость разблокирован');
    } catch (error) {
      pageError = normalizeError(error);
    }
  }

async function handleMarkLost() {
    if (!ensureWritable()) {
      return;
    }
    const submission = await requestCardAction('card.mark_lost', actionGuards.markLost, {
      guestName: lookupGuestName,
    });
    if (!submission) return;
    const visitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id;
    if (!visitId) {
      uiStore.notifyWarning('Пометить lost можно из активного визита с привязанной картой.');
      return;
    }

    try {
      await visitStore.reportLostCard({
        visitId,
        reason: submission.values.reasonCode || 'operator_marked_lost',
        comment: submission.values.comment || null,
      });
      const uid = selectedLookup?.card_uid;
      if (uid) cardsGuestsWorkflowStore.setSelectedLookup(await lostCardStore.resolveCard(uid));
      await visitStore.fetchActiveVisits();
      cardsGuestsWorkflowStore.setPendingScenario('reissue');
      cardsGuestsWorkflowStore.setReissueStatus('Карта переведена в lost. Для продолжения считайте новую карту и выполните перевыпуск.');
      uiStore.notifySuccess('Карта помечена как lost');
    } catch (error) {
      pageError = normalizeError(error);
    }
  }

  async function handleScenarioAction(event) {
    const { actionId } = event.detail;
    cardsGuestsWorkflowStore.setPendingScenario(actionId);
    const handler = resolveScenarioActionHandler(actionId);
    if (handler === 'open-top-up') {
      handleOpenTopUpModal();
      return;
    }
    if (handler === 'open-visit') {
      handleOpenVisit();
      return;
    }
    if (handler === 'open-history') {
      handleOpenHistory();
      return;
    }
    if (handler === 'toggle-block') {
      await handleToggleBlock();
      return;
    }
    if (handler === 'reissue') {
      reissueError = '';
      cardsGuestsWorkflowStore.setReissueStatus(buildReissueHint(selectedLookup));
    }
  }

  async function submitReissue() {
    if (!ensureWritable()) {
      return;
    }
    const nextUid = reissueUidInput.trim();
    const validation = validateReissueInput({ canReissue, selectedGuest, nextUid });
    if (!validation.ok) {
      uiStore.notifyWarning(validation.message);
      return;
    }
    isReissueBusy = true;
    reissueError = '';
    cardsGuestsWorkflowStore.setReissueStatus('');
    try {
      const targetVisitId = getReissueTargetVisitId({ selectedVisit, selectedLookup });
      if (!targetVisitId) {
        throw new Error('Перевыпуск доступен только для активного blocked-lost визита.');
      }
      await visitStore.reissueCard({
        visitId: targetVisitId,
        cardUid: nextUid,
        reason: 'lost_card_reissue',
        comment: null,
      });
      await Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()]);
      cardsGuestsWorkflowStore.setSelectedLookup(await lostCardStore.resolveCard(nextUid));
      cardsGuestsWorkflowStore.setSelectedGuestId(selectedGuest.guest_id);
      cardsGuestsWorkflowStore.setPendingScenario('open-visit');
      reissueUidInput = '';
      cardsGuestsWorkflowStore.setReissueStatus('Новая карта назначена этому активному визиту. Старый lost token остаётся в inventory state lost.');
      uiStore.notifySuccess('Перевыпуск карты завершён');
    } catch (error) {
      reissueError = normalizeError(error);
    } finally {
      isReissueBusy = false;
    }
  }

  async function handleSaveGuest(event) {
    if (!ensureWritable()) {
      return;
    }
    if (!hasManagementAccess) {
      uiStore.notifyWarning('Редактирование гостя недоступно для текущей роли.');
      return;
    }
    formError = '';
    try {
      await guestStore.updateGuest(selectedGuest.guest_id, event.detail);
      isManagementModalOpen = false;
      uiStore.notifySuccess('Данные гостя обновлены');
    } catch (error) {
      formError = normalizeError(error);
    }
  }

  function closeOperatorContext() {
    phoneQuery = '';
    cardsGuestsWorkflowStore.resetWorkflow();
  }

  onMount(async () => {
    await ensureCardsGuestsData({ reason: 'route-enter' });
  });
</script>

{#if !canAccessCardsGuests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает операции с картами и гостями.</p>
  </section>
{:else}
  <section class="cards-guests-page">
    <header class="page-header ui-card">
      <div>
        <h1>{ROUTE_COPY.cardsGuests.title}</h1>
        <p>{ROUTE_COPY.cardsGuests.description}</p>
      </div>
      <div class="header-actions">
        <DataFreshnessChip
          label="Cards & Guests"
          lastFetchedAt={$guestStore.lastFetchedAt || $visitStore.lastFetchedAt}
          staleAfterMs={Math.min($guestStore.staleTtlMs || 30000, $visitStore.staleTtlMs || 15000)}
          mode={$operatorConnectionStore.mode}
          transport={$operatorConnectionStore.transport}
          reason={$operatorConnectionStore.reason}
        />
        <button on:click={() => ensureCardsGuestsData({ reason: 'manual-refresh', force: true })} disabled={$guestStore.loading || $visitStore.loading}>Обновить данные</button>
      </div>
    </header>

    {#if routeReadOnlyReason}
      <section class="ui-card warning-banner">
        <strong>Read-only mode.</strong>
        <span>{routeReadOnlyReason}</span>
      </section>
    {/if}

    <CardLookupPanel
      title="Проверка карты и помощь гостю"
      description="Приложите карту, введите UID или найдите гостя по номеру, чтобы сразу увидеть статус карты, баланс, активный визит, последний кран и доступные действия."
      result={selectedLookup}
      searchQuery={phoneQuery}
      searchResults={quickLookupResults}
      operatorSummaryItems={lookupSummaryItems}
      searchPlaceholder="Номер телефона, UID или идентификатор"
      searchResultLabel="Поиск по номеру / идентификатору"
      error={lookupError}
      loading={$lostCardStore.loading || $visitStore.loading}
      allowRestoreLost={canReissue}
      restoreLostDisabled={Boolean(actionGuards.restoreLost?.disabled)}
      restoreLostReason={actionGuards.restoreLost?.reason || ''}
      allowOpenVisit={canOpenVisit}
      openVisitDisabled={Boolean(actionGuards.openVisit?.disabled)}
      openVisitReason={actionGuards.openVisit?.reason || ''}
      allowOpenGuest={Boolean(selectedGuest)}
      allowOpenNewVisit={false}
      openVisitLabel="Открыть активную сессию"
      openGuestLabel="Открыть контекст гостя"
      openNewVisitLabel="Открыть новый визит"
      actions={quickActions}
      selectedActionId={pendingScenario}
      on:lookup={handleLookup}
      on:restore-lost={handleRestoreLost}
      on:open-visit={handleOpenVisit}
      on:open-guest={(event) => selectGuest(event.detail.guestId)}
      on:open-new-visit={handleOpenNewVisit}
      on:scenario-action={handleScenarioAction}
      on:search-change={(event) => { phoneQuery = event.detail.value; }}
    />

    <section class="ui-card operator-panel">
      <div class="section-top">
        <div>
          <h2>Контекст гостя</h2>
          <p>После проверки карты здесь остаётся только короткий рабочий контекст: статус карты, баланс, визит, последний кран и последние действия.</p>
        </div>
        {#if pendingScenario}
          <span class="scenario-badge">{pendingScenarioLabel}</span>
        {/if}
      </div>

      {#if selectedGuest}
        <GuestDetail
          guest={selectedGuest}
          activeVisit={selectedVisit}
          cardLookup={selectedLookup}
          recentActivity={recentGuestPours}
          recentEvents={recentEvents}
          lastTapLabel={lastTapLabel}
          variant="operator"
          on:close={closeOperatorContext}
          canTopUp={canTopUp}
          topUpDisabled={Boolean(actionGuards.topUp?.disabled)}
          topUpReason={actionGuards.topUp?.reason || ''}
          canToggleBlock={canToggleBlock}
          toggleBlockDisabled={Boolean(actionGuards.toggleBlock?.disabled)}
          toggleBlockReason={actionGuards.toggleBlock?.reason || ''}
          canMarkLost={canReissue}
          markLostDisabled={Boolean(actionGuards.markLost?.disabled)}
          markLostReason={actionGuards.markLost?.reason || ''}
          canOpenHistory={canViewHistory}
          openHistoryDisabled={Boolean(actionGuards.openHistory?.disabled)}
          openHistoryReason={actionGuards.openHistory?.reason || ''}
          canOpenVisit={canOpenVisit}
          openVisitDisabled={Boolean(actionGuards.openVisit?.disabled)}
          openVisitReason={actionGuards.openVisit?.reason || ''}
          canManageProfile={hasManagementAccess}
          on:top-up={handleOpenTopUpModal}
          on:toggle-block={handleToggleBlock}
          on:mark-lost={handleMarkLost}
          on:open-history={handleOpenHistory}
          on:open-visit={handleOpenVisit}
          on:open-management={() => { if (!hasManagementAccess) { uiStore.notifyWarning('Редактирование гостя недоступно для текущей роли.'); return; } formError = ''; isManagementModalOpen = true; }}
        />
      {:else}
        <div class="empty-state">
          <h3>Сначала проверьте карту или гостя</h3>
          <p>После идентификации здесь появится короткая рабочая сводка: статус карты, баланс, активный визит, последний кран, события и быстрые действия.</p>
        </div>
      {/if}

      {#if pageError || $guestStore.error || $visitStore.error}
        <p class="error">{pageError || $guestStore.error || $visitStore.error}</p>
      {/if}
    </section>

    {#if hasLookup && (pendingScenario === 'reissue' || selectedLookup?.is_lost)}
      <section class="ui-card reissue-panel">
        <div class="section-top">
          <div>
            <h2>Перевыпуск и потерянные карты</h2>
            <p>Этот сценарий открывается только после проверки карты и не мешает основному рабочему контексту по гостю.</p>
          </div>
        </div>
        {#if selectedLookup?.is_lost}
          <div class="scenario-warning">
            <strong>Текущая карта отмечена как потерянная.</strong>
            <span>Отмечена {formatDateTimeRu(selectedLookup.lost_card?.reported_at)}.</span>
          </div>
        {/if}
        <div class="reissue-input-row">
          <input
            type="text"
            bind:value={reissueUidInput}
            placeholder="Считайте или введите UID новой карты"
            on:keydown={(event) => event.key === 'Enter' && submitReissue()}
          />
          <button on:click={submitReissue} disabled={isReissueBusy || !reissueUidInput.trim() || !selectedGuest}>Завершить перевыпуск</button>
        </div>
        <ol class="reissue-steps">
          <li>Подтвердите гостя: <strong>{lookupGuestName}</strong>.</li>
          <li>Перевыпуск доступен только для blocked-lost активного визита.</li>
          <li>Новая физическая карта будет назначена на тот же визит, а старая останется в состоянии lost.</li>
        </ol>
        {#if reissueStatus}
          <p class="reissue-status">{reissueStatus}</p>
        {/if}
        {#if reissueError}
          <p class="error">{reissueError}</p>
        {/if}
      </section>
    {/if}
  </section>

  {#if isTopUpModalOpen && selectedGuest}
    <TopUpModal
      guestName={fullName(selectedGuest)}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}

  {#if isManagementModalOpen && selectedGuest}
    <Modal on:close={() => { isManagementModalOpen = false; }}>
      <section class="management-modal">
        <div class="section-top">
          <div>
            <h2>Расширенное управление</h2>
            <p>Редактирование профиля и дополнительные поля вынесены из рабочего экрана в отдельный режим.</p>
          </div>
        </div>
        <GuestDetail
          guest={selectedGuest}
          activeVisit={selectedVisit}
          cardLookup={selectedLookup}
          recentActivity={recentGuestPours}
          recentEvents={recentEvents}
          lastTapLabel={lastTapLabel}
          variant="full"
          canTopUp={canTopUp}
          topUpDisabled={Boolean(actionGuards.topUp?.disabled)}
          topUpReason={actionGuards.topUp?.reason || ''}
          canToggleBlock={canToggleBlock}
          toggleBlockDisabled={Boolean(actionGuards.toggleBlock?.disabled)}
          toggleBlockReason={actionGuards.toggleBlock?.reason || ''}
          canMarkLost={canReissue}
          markLostDisabled={Boolean(actionGuards.markLost?.disabled)}
          markLostReason={actionGuards.markLost?.reason || ''}
          canOpenHistory={canViewHistory}
          openHistoryDisabled={Boolean(actionGuards.openHistory?.disabled)}
          openHistoryReason={actionGuards.openHistory?.reason || ''}
          canOpenVisit={canOpenVisit}
          openVisitDisabled={Boolean(actionGuards.openVisit?.disabled)}
          openVisitReason={actionGuards.openVisit?.reason || ''}
          canManageProfile={hasManagementAccess}
          on:top-up={handleOpenTopUpModal}
          on:toggle-block={handleToggleBlock}
          on:mark-lost={handleMarkLost}
          on:open-history={handleOpenHistory}
          on:open-visit={handleOpenVisit}
          on:edit={() => { formError = ''; }}
          on:bind-card={() => { cardsGuestsWorkflowStore.setPendingScenario('reissue'); isManagementModalOpen = false; }}
          on:close={() => { isManagementModalOpen = false; }}
        />
        <GuestForm guest={selectedGuest} on:save={handleSaveGuest} on:cancel={() => { isManagementModalOpen = false; }} isSaving={$guestStore.loading} />
      </section>
      {#if formError}<p class="error">{formError}</p>{/if}
    </Modal>
  {/if}
{/if}

<style>
  .cards-guests-page { display: grid; gap: 1rem; }
  .page-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; }
  .page-header h1, .page-header p { margin: 0; }
  .page-header p { color: var(--text-secondary); }
  .header-actions { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
  .operator-panel, .management-modal, .reissue-panel { display: grid; gap: 0.85rem; }
  .warning-banner { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; padding: 0.9rem 1rem; border: 1px solid #fcd34d; border-radius: 14px; background: #fff7ed; color: #9a3412; }
  .section-top { display: flex; justify-content: space-between; gap: 0.75rem; align-items: start; }
  .section-top h2, .section-top p { margin: 0; }
  .empty-state { min-height: 220px; display: grid; align-content: center; gap: 0.5rem; }
  .empty-state h3, .empty-state p { margin: 0; }
  .scenario-badge {
    border-radius: 999px; padding: 0.35rem 0.7rem; background: #eef2ff; color: #1d4ed8; font-weight: 700;
    text-transform: capitalize;
  }
  .scenario-warning {
    display: flex; justify-content: space-between; gap: 0.75rem; align-items: center;
    background: #fff7ed; border: 1px solid #fed7aa; border-radius: 12px; padding: 0.75rem 0.85rem;
  }
  .reissue-input-row { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  .reissue-input-row input { flex: 1 1 260px; }
  .reissue-steps { margin: 0; padding-left: 1.15rem; display: grid; gap: 0.35rem; }
  .reissue-status { margin: 0; color: #166534; font-weight: 600; }
  .error { color: #c61f35; margin: 0; }
  @media (max-width: 1024px) {
    .page-header, .section-top, .scenario-warning { flex-direction: column; align-items: start; }
  }
</style>
