<script>
  import { onMount } from 'svelte';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestStore } from '../stores/guestStore.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import {
    formatDateTimeRu,
    formatRubAmount,
    formatVisitStatus,
    formatVolumeRu,
  } from '../lib/formatters.js';

  let filterQuery = '';
  let forceUnlockReason = '';
  let forceUnlockComment = '';
  let closeReason = 'guest_checkout';
  let actionError = '';
  let reconcileOpen = false;
  let reconcileShortId = '';
  let reconcileVolumeMl = '';
  let reconcileAmount = '';
  let reconcileReason = 'sync_timeout';
  let reconcileComment = '';

  let openFlowVisible = false;
  let guestQuery = '';
  let openFlowError = '';
  let pendingOpenGuest = null;

  let isNFCModalOpen = false;
  let nfcMode = 'lookup';
  let nfcError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let isCurrentCardLost = false;
  let lostCardStatusText = '';
  let cardLookupResult = null;

  $: visit = $visitStore.currentVisit;
  $: selectedGuest = visit ? $guestStore.guests.find((g) => g.guest_id === visit.guest_id) : null;
  $: lockActive = visit?.active_tap_id !== null && visit?.active_tap_id !== undefined;
  $: lockAgeSeconds = visit?.lock_set_at ? Math.max(0, Math.floor((Date.now() - new Date(visit.lock_set_at).getTime()) / 1000)) : 0;
  $: suggestManualReconcile = lockAgeSeconds >= 60;
  $: isBlockedLostVisit = visit?.operational_status === 'active_blocked_lost_card';
  $: canManageLostRecovery = Boolean($roleStore.permissions.cards_reissue_manage);
  $: canUseMaintenanceActions = Boolean($roleStore.permissions.maintenance_actions);

  function requirePermission(permissionKey, message) {
    if ($roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  const fullName = (guestLike) => {
    if (!guestLike) return '—';
    if (guestLike.guest_full_name) return guestLike.guest_full_name;
    return [guestLike.last_name, guestLike.first_name, guestLike.patronymic].filter(Boolean).join(' ');
  };

  const visitOperationalLabel = (operationalStatus) => ({
    active_assigned: 'Активен, карта назначена',
    active_blocked_lost_card: 'Заблокирован: карта потеряна',
    closed_ok: 'Закрыт с подтверждённым возвратом карты',
    closed_missing_card: 'Закрыт сервисно без возврата карты',
  }[operationalStatus] || operationalStatus || '—');

  const matchesVisit = (item, query) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      (item.guest_full_name || '').toLowerCase().includes(q) ||
      (item.phone_number || '').toLowerCase().includes(q) ||
      (item.card_uid || '').toLowerCase().includes(q) ||
      (item.visit_id || '').toLowerCase().includes(q)
    );
  };

  $: filteredVisits = ($visitStore.activeVisits || []).filter((v) => matchesVisit(v, filterQuery));

  onMount(async () => {
    if ($guestStore.guests.length === 0 && !$guestStore.loading) {
      guestStore.fetchGuests();
    }
    await visitStore.fetchActiveVisits();
    const lookupVisitId = sessionStorage.getItem('visits.lookupVisitId');
    if (lookupVisitId) {
      sessionStorage.removeItem('visits.lookupVisitId');
      const target = ($visitStore.activeVisits || []).find((item) => item.visit_id === lookupVisitId);
      if (target) {
        selectVisit(target);
        filterQuery = lookupVisitId;
      }
    }
  });

  async function refreshVisits() {
    await visitStore.fetchActiveVisits();
    if (visit) {
      const fresh = ($visitStore.activeVisits || []).find((v) => v.visit_id === visit.visit_id);
      if (fresh) {
        visitStore.setCurrentVisit({ ...visit, ...fresh });
      }
    }
  }

  async function refreshCurrentLostStatus() {
    if (!visit?.card_uid) {
      isCurrentCardLost = false;
      lostCardStatusText = '';
      return;
    }
    try {
      const rows = await lostCardStore.fetchLostCards({
        uid: visit.card_uid,
        reportedFrom: '',
        reportedTo: '',
      });
      isCurrentCardLost = rows.length > 0;
      lostCardStatusText = isCurrentCardLost ? 'Карта помечена как потерянная' : '';
    } catch {
      isCurrentCardLost = false;
      lostCardStatusText = '';
    }
  }

  function startOpenFlow() {
    openFlowVisible = true;
    guestQuery = '';
    openFlowError = '';
  }

  $: openCandidates = ($guestStore.guests || []).filter((g) => {
    const q = guestQuery.trim().toLowerCase();
    if (!q) return false;
    const fio = fullName(g).toLowerCase();
    return fio.includes(q) || (g.phone_number || '').toLowerCase().includes(q);
  }).slice(0, 8);

  function openVisitWithCard(guest) {
    openFlowError = '';
    pendingOpenGuest = guest;
    nfcMode = 'open';
    nfcError = '';
    isNFCModalOpen = true;
  }

  function selectVisit(item) {
    const fromGuests = $guestStore.guests.find((g) => g.guest_id === item.guest_id);
    visitStore.setCurrentVisit({
      ...item,
      guest_id: item.guest_id,
      guest: fromGuests || null,
    });
    actionError = '';
    refreshCurrentLostStatus();
  }

  async function handleForceUnlock() {
    actionError = '';
    if (!visit) return;
    if (!requirePermission('maintenance_actions', 'Принудительная разблокировка доступна только сервисному уровню.')) return;
    if (!forceUnlockReason.trim()) {
      uiStore.notifyWarning('Причина обязательна для снятия блокировки.');
      return;
    }

    try {
      const updated = await visitStore.forceUnlock({
        visitId: visit.visit_id,
        reason: forceUnlockReason.trim(),
        comment: forceUnlockComment.trim() || null,
      });
      visitStore.setCurrentVisit(updated);
      await refreshVisits();
      uiStore.notifySuccess('Блокировка снята.');
      forceUnlockReason = '';
      forceUnlockComment = '';
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка снятия блокировки';
    }
  }

  async function handleCloseVisit() {
    actionError = '';
    if (!visit) return;
    nfcMode = 'close';
    nfcError = '';
    isNFCModalOpen = true;
  }

  async function handleReconcilePour() {
    actionError = '';
    if (!visit) return;
    if (!requirePermission('maintenance_actions', 'Ручная сверка и разблокировка доступны только сервисному уровню.')) return;
    if (!reconcileShortId.trim() || !reconcileVolumeMl || !reconcileAmount || !reconcileReason.trim()) {
      uiStore.notifyWarning('Заполните номер налива, объём, сумму и причину.');
      return;
    }

    try {
      const updated = await visitStore.reconcilePour({
        visitId: visit.visit_id,
        tapId: visit.active_tap_id,
        shortId: reconcileShortId.trim(),
        volumeMl: Number(reconcileVolumeMl),
        amount: String(reconcileAmount).trim(),
        reason: reconcileReason.trim(),
        comment: reconcileComment.trim() || null,
      });
      visitStore.setCurrentVisit(updated);
      await refreshVisits();
      reconcileOpen = false;
      reconcileShortId = '';
      reconcileVolumeMl = '';
      reconcileAmount = '';
      reconcileReason = 'sync_timeout';
      reconcileComment = '';
      uiStore.notifySuccess('Ручная сверка выполнена.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось выполнить ручную сверку';
    }
  }

  function handleReissueCard() {
    if (!visit) return;
    if (!requirePermission('cards_reissue_manage', 'Работа с потерянной картой и перевыпуск доступны только ролям с правом на перевыпуск карт.')) return;
    nfcMode = 'reissue';
    nfcError = '';
    isNFCModalOpen = true;
  }

  function handleLookupByCard() {
    nfcMode = 'lookup';
    nfcError = '';
    isNFCModalOpen = true;
  }

  function hasLookupVisitTarget() {
    return Boolean(cardLookupResult?.active_visit?.visit_id || cardLookupResult?.lost_card?.visit_id);
  }

  async function resolveByCardUid(cardUid) {
    actionError = '';
    try {
      cardLookupResult = await lostCardStore.resolveCard(cardUid);
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось получить статус карты';
      cardLookupResult = null;
      throw error;
    }
  }

  async function handleLookupRestoreLost() {
    if (!requirePermission('cards_reissue_manage', 'Снятие отметки потерянной карты доступно только ролям с перевыпуском и восстановлением карт.')) return;
    const uid = cardLookupResult?.card?.uid || cardLookupResult?.card_uid;
    if (!uid) return;
    try {
      await lostCardStore.restoreLostCard(uid);
      await resolveByCardUid(uid);
      await refreshVisits();
      await refreshCurrentLostStatus();
      uiStore.notifySuccess('Отметка потерянной карты снята');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось снять отметку потерянной карты';
    }
  }

  async function handleLookupOpenVisit() {
    const targetVisitId = cardLookupResult?.active_visit?.visit_id || cardLookupResult?.lost_card?.visit_id;
    if (!targetVisitId) return;
    await refreshVisits();
    const target = ($visitStore.activeVisits || []).find((item) => item.visit_id === targetVisitId);
    if (!target) {
      uiStore.notifyWarning('Визит не найден среди активных');
      filterQuery = targetVisitId;
      return;
    }
    selectVisit(target);
    filterQuery = targetVisitId;
    uiStore.notifySuccess('Открыт активный визит по карте');
  }

  async function handleLookupOpenNewVisit() {
    uiStore.notifyWarning('Новый визит открывается только по сценарию «выберите гостя и затем считайте карту». Если карта новая, система сама добавит её в пул.');
  }

  async function handleUidRead(event) {
    nfcError = '';
    if (nfcMode === 'lookup') {
      try {
        await resolveByCardUid(event.detail.uid);
      } catch (error) {
        nfcError = error?.message || error?.toString?.() || 'Не удалось выполнить поиск по карте';
      }
      return;
    }

    try {
      if (nfcMode === 'open') {
        if (!pendingOpenGuest?.guest_id) throw new Error('Не выбран гость для открытия визита.');
        const opened = await visitStore.openVisit({ guestId: pendingOpenGuest.guest_id, cardUid: event.detail.uid });
        visitStore.setCurrentVisit(opened);
        await refreshVisits();
        openFlowVisible = false;
        pendingOpenGuest = null;
        isNFCModalOpen = false;
        uiStore.notifySuccess('Визит открыт. Если карта была новой, система автоматически добавила её в пул.');
        return;
      }
      if (nfcMode === 'close') {
        const closed = await visitStore.closeVisit({
          visitId: visit.visit_id,
          closedReason: closeReason,
          returnedCardUid: event.detail.uid,
        });
        visitStore.setCurrentVisit(closed);
        await refreshVisits();
        isNFCModalOpen = false;
        uiStore.notifySuccess('Визит закрыт с подтверждённым возвратом карты.');
        return;
      }
      if (nfcMode === 'reissue') {
        const updated = await visitStore.reissueCard({
          visitId: visit.visit_id,
          cardUid: event.detail.uid,
          reason: 'lost_card_reissue',
          comment: null,
        });
        visitStore.setCurrentVisit(updated);
        await refreshVisits();
        await refreshCurrentLostStatus();
        isNFCModalOpen = false;
        uiStore.notifySuccess('Новая карта назначена активному визиту.');
        return;
      }
      throw new Error('Неизвестный NFC-сценарий.');
    } catch (error) {
      nfcError = error?.message || error?.toString?.() || 'Не удалось выполнить NFC-действие';
    }
  }

  function handleOpenTopUpModal() {
    if (!visit) return;
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    topUpError = '';
    try {
      await guestStore.topUpBalance(visit.guest_id, event.detail);
      await refreshVisits();
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Баланс пополнен на ${formatRubAmount(event.detail.amount)}`);
    } catch (error) {
      topUpError = error?.message || error?.toString?.() || 'Ошибка пополнения баланса';
    }
  }

  async function handleReportLostCard() {
    actionError = '';
    if (!visit || !visit.card_uid) return;
    if (!requirePermission('cards_reissue_manage', 'Отметка потерянной карты доступна только ролям с перевыпуском и восстановлением карт.')) return;

    const confirmed = await uiStore.confirm({
      title: 'Отметить карту потерянной',
      message: `Пометить карту ${visit.card_uid} как потерянную?`,
      confirmText: 'Отметить',
      cancelText: 'Отмена',
      danger: true,
    });
    if (!confirmed) return;

    const rawComment = window.prompt('Комментарий (опционально)', '');
    if (rawComment === null) return;

    try {
      const result = await visitStore.reportLostCard({
        visitId: visit.visit_id,
        reason: 'guest_reported_loss',
        comment: rawComment.trim() || null,
      });
      await refreshVisits();
      isCurrentCardLost = true;
      lostCardStatusText = result.already_marked
        ? 'Карта уже была помечена как потерянная'
        : 'Карта помечена как потерянная';
      uiStore.notifySuccess(lostCardStatusText);
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка отметки потерянной карты';
    }
  }

  async function handleCancelLost() {
    actionError = '';
    if (!visit || !isBlockedLostVisit) return;
    if (!requirePermission('cards_reissue_manage', 'Снятие отметки потерянной карты для активного визита доступно только ролям с перевыпуском и восстановлением карт.')) return;

    const confirmed = await uiStore.confirm({
      title: 'Снять отметку потери с активного визита',
      message: `Вернуть карту ${visit.card_uid} в активный визит и отменить сценарий восстановления?`,
      confirmText: 'Снять отметку',
      cancelText: 'Отмена',
      danger: false,
    });
    if (!confirmed) return;

    const rawComment = window.prompt('Комментарий к снятию отметки потери (опционально)', '');
    if (rawComment === null) return;

    try {
      const restored = await visitStore.restoreLostCardForVisit({
        visitId: visit.visit_id,
        reason: 'card_recovered',
        comment: rawComment.trim() || null,
      });
      visitStore.setCurrentVisit(restored);
      await refreshVisits();
      await refreshCurrentLostStatus();
      uiStore.notifySuccess('Отметка потери снята, визит снова активен с той же картой.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось снять отметку потери для визита';
    }
  }

  async function handleServiceClose() {
    actionError = '';
    if (!visit) return;
    if (!requirePermission('maintenance_actions', 'Сервисное закрытие визита без возврата карты доступно только сервисному уровню.')) return;
    const rawComment = window.prompt('Комментарий к сервисному закрытию (опционально)', '');
    if (rawComment === null) return;
    try {
      const closed = await visitStore.serviceCloseVisit({
        visitId: visit.visit_id,
        closedReason: 'service_close_missing_card',
        reasonCode: 'card_missing',
        comment: rawComment.trim() || null,
      });
      visitStore.setCurrentVisit(closed);
      await refreshVisits();
      await refreshCurrentLostStatus();
      uiStore.notifySuccess('Визит закрыт сервисным сценарием без возврата карты.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось сервисно закрыть визит';
    }
  }
</script>

{#if !$roleStore.permissions.sessions_view}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с визитами.</p>
  </section>
{:else}
  <section class="ui-card open-section">
    <h1>Визиты</h1>
    <button class="primary-open" on:click={startOpenFlow}>Открыть новый визит</button>

    {#if openFlowVisible}
      <div class="open-flow">
        <h2>Открытие визита</h2>
        <p class="hint">Найдите гостя по ФИО или телефону, затем приложите карту для открытия визита. Если карта новая, система автоматически добавит её в пул.</p>
        <input type="text" bind:value={guestQuery} placeholder="ФИО / телефон" />

        {#if guestQuery.trim() && openCandidates.length === 0}
          <p class="not-found">Гость не найден</p>
        {/if}

        {#if openCandidates.length > 0}
          <div class="open-candidates">
            {#each openCandidates as candidate}
              <button class="candidate-item" on:click={() => openVisitWithCard(candidate)} disabled={$visitStore.loading}>
                <div><strong>{fullName(candidate)}</strong></div>
                <div>{candidate.phone_number} · Баланс: {formatRubAmount(candidate.balance)}</div>
              </button>
            {/each}
          </div>
        {/if}

        {#if openFlowError}
          <p class="error">{openFlowError}</p>
        {/if}
      </div>
    {/if}
  </section>

  <div class="visits-layout">
    <section class="ui-card list-panel">
      <div class="list-header">
        <h2>Список активных визитов</h2>
        <div class="list-actions">
          <button on:click={refreshVisits} disabled={$visitStore.loading}>Обновить</button>
          <button on:click={handleLookupByCard} disabled={$visitStore.loading}>Найти по карте (NFC)</button>
        </div>
      </div>
      <input type="text" bind:value={filterQuery} placeholder="Фильтр: ФИО / телефон / карта / ID визита" />

      <CardLookupPanel
        title="Результат поиска по карте"
        description="Единая проверка карты для сессий, потерянных карт и карточки гостя."
        result={cardLookupResult}
        error={actionError}
        loading={$lostCardStore.loading || $visitStore.loading}
        allowRestoreLost={canManageLostRecovery}
        allowOpenVisit={hasLookupVisitTarget()}
        allowOpenGuest={false}
        allowOpenNewVisit={false}
        on:lookup={(event) => resolveByCardUid(event.detail.uid).catch((error) => { nfcError = error?.message || error?.toString?.() || 'Не удалось выполнить поиск по карте'; })}
        on:restore-lost={handleLookupRestoreLost}
        on:open-visit={handleLookupOpenVisit}
        on:open-new-visit={handleLookupOpenNewVisit}
      />

      {#if $visitStore.loading && $visitStore.activeVisits.length === 0}
        <p>Загрузка активных визитов...</p>
      {:else if filteredVisits.length === 0}
        <p class="not-found">Визит не найден</p>
      {:else}
        <div class="visit-list">
          {#each filteredVisits as item}
            <button class="visit-item" on:click={() => selectVisit(item)}>
              <div><strong>{item.guest_full_name}</strong></div>
              <div>{item.phone_number}</div>
              <div>Карта: {item.card_uid}</div>
              <div>{visitOperationalLabel(item.operational_status)}</div>
              {#if item.active_tap_id}
                <div class="sync-indicator">Идёт синхронизация налива на кране #{item.active_tap_id}</div>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <section class="ui-card detail-panel">
      {#if visit}
        <h2>Карточка визита</h2>
        <div class="visit-fields">
          <div><strong>Гость:</strong> {fullName(selectedGuest || visit)}</div>
          <div><strong>Телефон:</strong> {selectedGuest?.phone_number || visit.phone_number || '—'}</div>
          <div><strong>Карта:</strong> {visit.card_uid}</div>
          <div><strong>Статус визита:</strong> {formatVisitStatus(visit.status)}</div>
          <div><strong>Операционный статус:</strong> {visitOperationalLabel(visit.operational_status)}</div>
          <div><strong>Баланс:</strong> {formatRubAmount(selectedGuest?.balance ?? visit.balance ?? 0)}</div>
          {#if isCurrentCardLost}
            <div class="lost-status"><strong>Статус карты:</strong> {lostCardStatusText || 'Карта помечена как потерянная'}</div>
          {/if}
        </div>

        {#if isBlockedLostVisit}
          <div class="recovery-banner">
            <strong>Визит заблокирован из-за потерянной карты</strong>
            <p>Здесь доступен полный сценарий восстановления: перевыпуск на новую карту, снятие отметки потери с текущей карты или сервисное закрытие без возврата карты.</p>
          </div>
        {/if}

        <div class="lock-state" class:locked={lockActive} class:free={!lockActive}>
          {#if lockActive}
            <strong>Блокировка на кране №{visit.active_tap_id}</strong>
            {#if visit.lock_set_at}
              <div>Блокировка установлена: {formatDateTimeRu(visit.lock_set_at)}</div>
              <div>Возраст блокировки: около {Math.floor(lockAgeSeconds / 60)} мин</div>
            {/if}
            <div>Синхронизация: {suggestManualReconcile ? 'Нужна ручная сверка' : 'Ожидается синхронизация'}</div>
          {:else}
            <strong>Кран свободен</strong>
          {/if}
        </div>

        <div class="actions-grid">
          {#if isBlockedLostVisit}
            <div class="action-panel recovery-panel">
              <h3>Восстановление визита</h3>
              <p class="hint">Это обязательный сценарий восстановления: доступны перевыпуск, снятие отметки потери и сервисное закрытие.</p>
              <button on:click={handleReissueCard} disabled={$visitStore.loading || !canManageLostRecovery}>Считать новую карту и перевыпустить</button>
              <button on:click={handleCancelLost} disabled={$visitStore.loading || !canManageLostRecovery}>Снять отметку потери и оставить текущую карту</button>
              <button class="secondary" on:click={handleServiceClose} disabled={$visitStore.loading || !canUseMaintenanceActions}>Сервисно закрыть без возврата карты</button>
            </div>
          {:else}
            <div class="action-panel">
              <h3>Принудительно снять блокировку</h3>
              <input type="text" bind:value={forceUnlockReason} placeholder="Причина (обязательно)" />
              <textarea bind:value={forceUnlockComment} rows="2" placeholder="Комментарий (опционально)"></textarea>
              <button on:click={handleForceUnlock} disabled={$visitStore.loading || !lockActive || !canUseMaintenanceActions}>Принудительно снять блокировку</button>
              <button on:click={() => (reconcileOpen = true)} disabled={$visitStore.loading || !lockActive || !canUseMaintenanceActions}>Ручная сверка / разблокировать</button>
            </div>

            <div class="action-panel">
              <h3>Закрыть визит</h3>
              <input type="text" bind:value={closeReason} placeholder="Причина закрытия" />
              <button on:click={handleCloseVisit} disabled={$visitStore.loading || visit.status !== 'active' || visit.operational_status !== 'active_assigned'}>Считать карту и закрыть визит</button>
            </div>

            <div class="action-panel">
              <h3>Операции</h3>
              <button
                class="danger-btn"
                on:click={handleReportLostCard}
                disabled={$visitStore.loading || isCurrentCardLost || !canManageLostRecovery || visit.operational_status !== 'active_assigned'}
              >
                Отметить карту потерянной
              </button>
              <button on:click={handleOpenTopUpModal} disabled={$visitStore.loading}>Пополнить баланс</button>
            </div>
          {/if}
        </div>

        {#if actionError || $visitStore.error}
          <p class="error">{actionError || $visitStore.error}</p>
        {/if}
      {:else}
        <div class="empty-state">
          <h3>Визит не выбран</h3>
          <p>Выберите визит из списка слева.</p>
        </div>
      {/if}
    </section>
  </div>

  {#if reconcileOpen && visit}
    <section class="ui-card reconcile-modal">
      <h3>Ручная сверка налива</h3>
      <input type="text" bind:value={reconcileShortId} placeholder="Короткий номер налива (6-8 символов)" maxlength="8" />
      <input type="number" bind:value={reconcileVolumeMl} placeholder="Объём, мл" min="1" />
      <input type="number" bind:value={reconcileAmount} placeholder="Сумма, ₽" min="0.01" step="0.01" />
      <input type="text" bind:value={reconcileReason} placeholder="Причина сверки" />
      <textarea bind:value={reconcileComment} rows="2" placeholder="Комментарий (необязательно)"></textarea>
      <div class="modal-actions">
        <button on:click={handleReconcilePour} disabled={$visitStore.loading}>Отправить</button>
        <button on:click={() => (reconcileOpen = false)} disabled={$visitStore.loading}>Отмена</button>
      </div>
    </section>
  {/if}

  {#if isNFCModalOpen}
    <NFCModal
      on:close={() => { isNFCModalOpen = false; pendingOpenGuest = null; }}
      on:uid-read={handleUidRead}
      externalError={nfcError}
    />
  {/if}

  {#if isTopUpModalOpen && visit}
    <TopUpModal
      guestName={fullName(selectedGuest || visit)}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}
{/if}

<style>
  .open-section { margin-bottom: 1rem; }
  .primary-open { margin-bottom: 0.75rem; }
  .open-flow {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    background: var(--bg-surface-muted);
    padding: 0.75rem;
    display: grid;
    gap: 0.75rem;
  }
  .hint { margin: 0; color: var(--text-secondary); }
  .open-candidates { display: grid; gap: 0.5rem; }
  .candidate-item {
    text-align: left;
    background: #fff;
    color: var(--text-primary);
    border: 1px solid var(--border-soft);
  }

  .visits-layout { display: grid; grid-template-columns: minmax(320px, 420px) 1fr; gap: 1rem; }
  .list-panel, .detail-panel { display: grid; gap: 0.75rem; align-content: start; }
  .list-header { display: flex; justify-content: space-between; align-items: center; }
  .list-header h2 { margin: 0; }
  .list-actions { display: flex; gap: 0.5rem; }


  .visit-list { display: grid; gap: 0.5rem; }
  .visit-item {
    text-align: left;
    background: #fff;
    color: var(--text-primary);
    border: 1px solid var(--border-soft);
  }

  .sync-indicator { color: #8a5a00; font-size: 0.85rem; font-weight: 600; }
  .visit-fields { display: grid; gap: 0.4rem; }

  .lock-state { border-radius: 10px; padding: 0.75rem 1rem; border: 1px solid var(--border-soft); }
  .lock-state.locked { background: #fff3cd; border-color: #f0ad4e; color: #8a5a00; }
  .lock-state.free { background: #e9f7ef; border-color: #7bc697; color: #1f6b3d; }
  .recovery-banner {
    border-radius: 10px;
    padding: 0.85rem 1rem;
    border: 1px solid #f0ad4e;
    background: #fff3cd;
    color: #8a5a00;
    display: grid;
    gap: 0.35rem;
  }
  .recovery-banner p { margin: 0; }

  .actions-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .action-panel {
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 0.75rem;
    display: grid;
    gap: 0.5rem;
  }
  .recovery-panel {
    border-color: #f0ad4e;
    background: #fffaf0;
  }
  .action-panel h3 { margin: 0; }

  .error { color: #c61f35; }
  .lost-status { color: #8a5a00; font-weight: 600; }
  .danger-btn { background: #b54234; color: #fff; }
  .not-found { color: var(--text-secondary); font-weight: 600; }
  .empty-state p { color: var(--text-secondary); }
  .reconcile-modal { margin-top: 1rem; display: grid; gap: 0.5rem; }
  .modal-actions { display: flex; gap: 0.5rem; }
</style>
