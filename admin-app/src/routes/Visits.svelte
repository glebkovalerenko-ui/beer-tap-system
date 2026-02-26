<script>
  import { onMount } from 'svelte';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestStore } from '../stores/guestStore.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';

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

  let isNFCModalOpen = false;
  let nfcMode = 'bind';
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

  const fullName = (guestLike) => {
    if (!guestLike) return '—';
    if (guestLike.guest_full_name) return guestLike.guest_full_name;
    return [guestLike.last_name, guestLike.first_name, guestLike.patronymic].filter(Boolean).join(' ');
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleString('ru-RU');
  };

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

  async function openVisitWithoutCard(guest) {
    openFlowError = '';
    try {
      const opened = await visitStore.openVisit({ guestId: guest.guest_id });
      visitStore.setCurrentVisit(opened);
      await refreshVisits();
      uiStore.notifySuccess('Визит открыт.');
      openFlowVisible = false;
    } catch (error) {
      const message = error?.message || error?.toString?.() || 'Ошибка открытия визита';
      openFlowError = message;
    }
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

    try {
      const closed = await visitStore.closeVisit({
        visitId: visit.visit_id,
        closedReason: closeReason,
        cardReturned: true,
      });
      visitStore.setCurrentVisit(closed);
      await refreshVisits();
      uiStore.notifySuccess('Визит закрыт.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка закрытия визита';
    }
  }

  async function handleReconcilePour() {
    actionError = '';
    if (!visit) return;
    if (!reconcileShortId.trim() || !reconcileVolumeMl || !reconcileAmount || !reconcileReason.trim()) {
      uiStore.notifyWarning('Fill short_id, volume, amount and reason');
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
      uiStore.notifySuccess('Manual reconcile completed');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Manual reconcile failed';
    }
  }

  function handleBindCard() {
    if (!visit) return;
    nfcMode = 'bind';
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
    const guestId = cardLookupResult?.guest?.guest_id;
    if (!guestId) return;
    try {
      const opened = await visitStore.openVisit({ guestId });
      visitStore.setCurrentVisit(opened);
      await refreshVisits();
      if (cardLookupResult?.card_uid) {
        await resolveByCardUid(cardLookupResult.card_uid);
      }
      uiStore.notifySuccess('Открыт новый визит для гостя');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось открыть новый визит';
    }
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
      await visitStore.assignCardToVisit({ visitId: visit.visit_id, cardUid: event.detail.uid });
      await refreshVisits();
      uiStore.notifySuccess('Карта успешно привязана к визиту.');
    } catch (error) {
      nfcError = error?.message || error?.toString?.() || 'Не удалось привязать карту к визиту';
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
      uiStore.notifySuccess(`Баланс пополнен на ${event.detail.amount}`);
    } catch (error) {
      topUpError = error?.message || error?.toString?.() || 'Ошибка пополнения баланса';
    }
  }

  async function handleReportLostCard() {
    actionError = '';
    if (!visit || !visit.card_uid) return;

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
</script>

{#if !$roleStore.permissions.guests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с визитами.</p>
  </section>
{:else}
  <section class="ui-card open-section">
    <h1>Активные визиты</h1>
    <button class="primary-open" on:click={startOpenFlow}>Открыть новый визит</button>

    {#if openFlowVisible}
      <div class="open-flow">
        <h2>Открытие визита</h2>
        <p class="hint">Найдите гостя по ФИО или телефону и выберите его из списка.</p>
        <input type="text" bind:value={guestQuery} placeholder="ФИО / телефон" />

        {#if guestQuery.trim() && openCandidates.length === 0}
          <p class="not-found">Гость не найден</p>
        {/if}

        {#if openCandidates.length > 0}
          <div class="open-candidates">
            {#each openCandidates as candidate}
              <button class="candidate-item" on:click={() => openVisitWithoutCard(candidate)} disabled={$visitStore.loading}>
                <div><strong>{fullName(candidate)}</strong></div>
                <div>{candidate.phone_number} В· Баланс: {candidate.balance}</div>
              </button>
            {/each}
          </div>
        {/if}

        <button disabled title="Выдача карты будет добавлена отдельным шагом">Выдача карты будет добавлена отдельным шагом</button>

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

      {#if cardLookupResult}
        <div class="lookup-card">
          <h3>Результат поиска по карте</h3>
          <div class="lookup-meta">
            <div><strong>UID:</strong> {cardLookupResult.card_uid}</div>
          </div>

          {#if cardLookupResult.is_lost}
            <p class="lookup-status lookup-status-danger">Карта отмечена как потерянная</p>
            <div class="lookup-meta">
              <div><strong>Дата отметки:</strong> {formatDateTime(cardLookupResult.lost_card?.reported_at)}</div>
              <div><strong>Комментарий:</strong> {cardLookupResult.lost_card?.comment || '—'}</div>
              <div><strong>Визит:</strong> {cardLookupResult.lost_card?.visit_id || '—'}</div>
            </div>
            <div class="lookup-actions">
              <button class="danger-btn" on:click={handleLookupRestoreLost} disabled={$lostCardStore.loading}>
                Снять отметку потерянной
              </button>
              {#if hasLookupVisitTarget()}
                <button on:click={handleLookupOpenVisit}>Открыть визит</button>
              {/if}
            </div>
          {:else if cardLookupResult.active_visit}
            <p class="lookup-status lookup-status-warning">Карта используется в активном визите</p>
            <div class="lookup-meta">
              <div><strong>Гость:</strong> {cardLookupResult.active_visit.guest_full_name}</div>
              <div><strong>Телефон:</strong> {cardLookupResult.active_visit.phone_number || '—'}</div>
              <div><strong>Визит:</strong> {cardLookupResult.active_visit.visit_id}</div>
              <div>
                <strong>Лок:</strong>
                {#if cardLookupResult.active_visit.active_tap_id}
                  Занята на кране #{cardLookupResult.active_visit.active_tap_id}
                {:else}
                  Нет активного лока
                {/if}
              </div>
            </div>
            <div class="lookup-actions">
              <button on:click={handleLookupOpenVisit}>Открыть карточку визита</button>
            </div>
          {:else if cardLookupResult.guest}
            <p class="lookup-status lookup-status-info">Карта привязана к гостю, активного визита нет</p>
            <div class="lookup-meta">
              <div><strong>Гость:</strong> {cardLookupResult.guest.full_name}</div>
              <div><strong>Телефон:</strong> {cardLookupResult.guest.phone_number || '—'}</div>
            </div>
            <div class="lookup-actions">
              <button on:click={handleLookupOpenNewVisit}>Открыть новый визит этому гостю</button>
            </div>
          {:else if cardLookupResult.card}
            <p class="lookup-status lookup-status-muted">Карта зарегистрирована, но не привязана к гостю</p>
          {:else}
            <p class="lookup-status lookup-status-muted">Карта не зарегистрирована в системе</p>
          {/if}
        </div>
      {/if}

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
              <div>{item.card_uid ? `Карта: ${item.card_uid}` : 'Без карты'}</div>
              {#if item.active_tap_id}
                <div class="sync-indicator">processing_sync (tap {item.active_tap_id})</div>
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
          <div><strong>Карта:</strong> {visit.card_uid || 'Не привязана'}</div>
          <div><strong>Статус:</strong> {visit.status}</div>
          <div><strong>Баланс:</strong> {selectedGuest?.balance ?? visit.balance ?? '—'}</div>
          {#if isCurrentCardLost}
            <div class="lost-status"><strong>Статус карты:</strong> {lostCardStatusText || 'Карта помечена как потерянная'}</div>
          {/if}
        </div>

        <div class="lock-state" class:locked={lockActive} class:free={!lockActive}>
          {#if lockActive}
            <strong>Блокировка на кране в„–{visit.active_tap_id}</strong>
            {#if visit.lock_set_at}
              <div>lock_set_at: {new Date(visit.lock_set_at).toLocaleString()}</div>
              <div>age: ~{Math.floor(lockAgeSeconds / 60)} min</div>
            {/if}
            <div>Синхронизация: {suggestManualReconcile ? 'Нужна ручная сверка' : 'Ожидается sync'}</div>
          {:else}
            <strong>Кран свободен</strong>
          {/if}
        </div>

        <div class="actions-grid">
          <div class="action-panel">
            <h3>Принудительно снять блокировку</h3>
            <input type="text" bind:value={forceUnlockReason} placeholder="Причина (обязательно)" />
            <textarea bind:value={forceUnlockComment} rows="2" placeholder="Комментарий (опционально)"></textarea>
            <button on:click={handleForceUnlock} disabled={$visitStore.loading || !lockActive}>Принудительно снять блокировку</button>
            <button on:click={() => (reconcileOpen = true)} disabled={$visitStore.loading || !lockActive}>Ручная сверка / разблокировать</button>
          </div>

          <div class="action-panel">
            <h3>Закрыть визит</h3>
            <input type="text" bind:value={closeReason} placeholder="Причина закрытия" />
            <button on:click={handleCloseVisit} disabled={$visitStore.loading || visit.status !== 'active'}>Закрыть визит</button>
          </div>

          <div class="action-panel">
            <h3>Операции</h3>
            {#if !visit.card_uid}
              <button on:click={handleBindCard} disabled={$visitStore.loading}>Привязать карту</button>
            {/if}
            {#if visit.card_uid}
              <button
                class="danger-btn"
                on:click={handleReportLostCard}
                disabled={$visitStore.loading || isCurrentCardLost}
              >
                Отметить карту потерянной
              </button>
            {/if}
            <button on:click={handleOpenTopUpModal} disabled={$visitStore.loading}>Пополнить баланс</button>
          </div>
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
      <input type="text" bind:value={reconcileShortId} placeholder="short_id (6-8)" maxlength="8" />
      <input type="number" bind:value={reconcileVolumeMl} placeholder="volume_ml" min="1" />
      <input type="number" bind:value={reconcileAmount} placeholder="amount" min="0.01" step="0.01" />
      <input type="text" bind:value={reconcileReason} placeholder="reason" />
      <textarea bind:value={reconcileComment} rows="2" placeholder="comment (optional)"></textarea>
      <div class="modal-actions">
        <button on:click={handleReconcilePour} disabled={$visitStore.loading}>Отправить</button>
        <button on:click={() => (reconcileOpen = false)} disabled={$visitStore.loading}>Отмена</button>
      </div>
    </section>
  {/if}

  {#if isNFCModalOpen}
    <NFCModal
      on:close={() => { isNFCModalOpen = false; }}
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

  .lookup-card {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    background: var(--bg-surface-muted);
    padding: 0.75rem;
    display: grid;
    gap: 0.5rem;
  }
  .lookup-card h3 { margin: 0; }
  .lookup-meta { display: grid; gap: 0.25rem; }
  .lookup-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .lookup-status { margin: 0; font-weight: 700; }
  .lookup-status-danger { color: #c61f35; }
  .lookup-status-warning { color: #8a5a00; }
  .lookup-status-info { color: #1f4a7c; }
  .lookup-status-muted { color: var(--text-secondary); }

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

  .actions-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .action-panel {
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 0.75rem;
    display: grid;
    gap: 0.5rem;
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
