<script>
  import { onMount } from 'svelte';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestStore } from '../stores/guestStore.js';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';

  let filterQuery = '';
  let forceUnlockReason = '';
  let forceUnlockComment = '';
  let closeReason = 'guest_checkout';
  let actionError = '';

  let openFlowVisible = false;
  let guestQuery = '';
  let openFlowError = '';

  let isNFCModalOpen = false;
  let nfcError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';

  $: visit = $visitStore.currentVisit;
  $: selectedGuest = visit ? $guestStore.guests.find((g) => g.guest_id === visit.guest_id) : null;
  $: lockActive = visit?.active_tap_id !== null && visit?.active_tap_id !== undefined;

  const fullName = (guestLike) => {
    if (!guestLike) return '—';
    if (guestLike.guest_full_name) return guestLike.guest_full_name;
    return [guestLike.last_name, guestLike.first_name, guestLike.patronymic].filter(Boolean).join(' ');
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

  function handleBindCard() {
    if (!visit) return;
    nfcError = '';
    isNFCModalOpen = true;
  }

  async function handleUidRead(event) {
    nfcError = '';
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
                <div>{candidate.phone_number} · Баланс: {candidate.balance}</div>
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
        <button on:click={refreshVisits} disabled={$visitStore.loading}>Обновить</button>
      </div>
      <input type="text" bind:value={filterQuery} placeholder="Фильтр: ФИО / телефон / карта / идентификатор визита" />

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
        </div>

        <div class="lock-state" class:locked={lockActive} class:free={!lockActive}>
          {#if lockActive}
            <strong>Блокировка на кране №{visit.active_tap_id}</strong>
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

  .visit-list { display: grid; gap: 0.5rem; }
  .visit-item {
    text-align: left;
    background: #fff;
    color: var(--text-primary);
    border: 1px solid var(--border-soft);
  }

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
  .not-found { color: var(--text-secondary); font-weight: 600; }
  .empty-state p { color: var(--text-secondary); }
</style>
