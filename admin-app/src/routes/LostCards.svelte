<script>
  import { onMount } from 'svelte';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import NFCModal from '../components/modals/NFCModal.svelte';

  let uidFilter = '';
  let reportedFrom = '';
  let reportedTo = '';
  let actionError = '';
  let isNFCModalOpen = false;
  let nfcError = '';
  let cardLookupResult = null;

  const toIsoOrNull = (value) => {
    if (!value || !value.trim()) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  };

  const formatDateTime = (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleString('ru-RU');
  };

  async function refresh() {
    actionError = '';
    await lostCardStore.fetchLostCards({
      uid: uidFilter,
      reportedFrom: toIsoOrNull(reportedFrom) || '',
      reportedTo: toIsoOrNull(reportedTo) || '',
    });
  }

  async function onRestore(item) {
    actionError = '';
    const ok = await uiStore.confirm({
      title: 'Снять отметку потери',
      message: `Снять отметку для карты ${item.card_uid}?`,
      confirmText: 'Снять отметку',
      cancelText: 'Отмена',
      danger: false,
    });
    if (!ok) return;

    try {
      await lostCardStore.restoreLostCard(item.card_uid);
      uiStore.notifySuccess('Отметка снята');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось снять отметку';
    }
  }

  function handleLookupByCard() {
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

  async function handleUidRead(event) {
    nfcError = '';
    try {
      await resolveByCardUid(event.detail.uid);
    } catch (error) {
      nfcError = error?.message || error?.toString?.() || 'Не удалось выполнить поиск по карте';
    }
  }

  async function handleLookupRestoreLost() {
    const uid = cardLookupResult?.card?.uid || cardLookupResult?.card_uid;
    if (!uid) return;
    try {
      await lostCardStore.restoreLostCard(uid);
      await resolveByCardUid(uid);
      uiStore.notifySuccess('Отметка потерянной карты снята');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось снять отметку потерянной карты';
    }
  }

  function handleLookupOpenVisit() {
    const targetVisitId = cardLookupResult?.active_visit?.visit_id || cardLookupResult?.lost_card?.visit_id;
    if (!targetVisitId) return;
    sessionStorage.setItem('visits.lookupVisitId', targetVisitId);
    window.location.hash = '/visits';
  }

  async function handleLookupOpenNewVisit() {
    const guestId = cardLookupResult?.guest?.guest_id;
    if (!guestId) return;
    try {
      const opened = await visitStore.openVisit({ guestId });
      sessionStorage.setItem('visits.lookupVisitId', opened.visit_id);
      window.location.hash = '/visits';
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось открыть новый визит';
    }
  }

  onMount(async () => {
    await refresh();
  });
</script>

{#if !$roleStore.permissions.guests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с потерянными картами.</p>
  </section>
{:else}
  <section class="ui-card panel">
    <h1>Потерянные карты</h1>

    <div class="filters">
      <input type="text" bind:value={uidFilter} placeholder="Поиск по UID" />
      <input type="datetime-local" bind:value={reportedFrom} />
      <input type="datetime-local" bind:value={reportedTo} />
      <button on:click={refresh} disabled={$lostCardStore.loading}>Найти</button>
      <button on:click={handleLookupByCard} disabled={$lostCardStore.loading}>Найти по карте (NFC)</button>
    </div>

    {#if cardLookupResult}
      <div class="lookup-card">
        <h2>Результат поиска по карте</h2>
        <div><strong>UID:</strong> {cardLookupResult.card_uid}</div>

        {#if cardLookupResult.is_lost}
          <p class="lookup-status lookup-status-danger">Карта отмечена как потерянная</p>
          <div><strong>Дата отметки:</strong> {formatDateTime(cardLookupResult.lost_card?.reported_at)}</div>
          <div><strong>Комментарий:</strong> {cardLookupResult.lost_card?.comment || '—'}</div>
          <div><strong>Визит:</strong> {cardLookupResult.lost_card?.visit_id || '—'}</div>
          <div class="lookup-actions">
            <button on:click={handleLookupRestoreLost} disabled={$lostCardStore.loading}>Снять отметку потерянной</button>
            {#if hasLookupVisitTarget()}
              <button on:click={handleLookupOpenVisit}>Открыть визит</button>
            {/if}
          </div>
        {:else if cardLookupResult.active_visit}
          <p class="lookup-status lookup-status-warning">Карта используется в активном визите</p>
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
          <div class="lookup-actions">
            <button on:click={handleLookupOpenVisit}>Открыть карточку визита</button>
          </div>
        {:else if cardLookupResult.guest}
          <p class="lookup-status lookup-status-info">Карта привязана к гостю, активного визита нет</p>
          <div><strong>Гость:</strong> {cardLookupResult.guest.full_name}</div>
          <div><strong>Телефон:</strong> {cardLookupResult.guest.phone_number || '—'}</div>
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

    {#if $lostCardStore.loading}
      <p>Загрузка...</p>
    {:else if ($lostCardStore.items || []).length === 0}
      <p class="hint">Записи не найдены</p>
    {:else}
      <div class="list">
        {#each $lostCardStore.items as item}
          <div class="row">
            <div><strong>{item.card_uid}</strong></div>
            <div>reported_at: {new Date(item.reported_at).toLocaleString()}</div>
            <div>reason: {item.reason || '—'}</div>
            <div>comment: {item.comment || '—'}</div>
            <div>visit_id: {item.visit_id || '—'}</div>
            <button on:click={() => onRestore(item)} disabled={$lostCardStore.loading}>Снять отметку</button>
          </div>
        {/each}
      </div>
    {/if}

    {#if actionError || $lostCardStore.error}
      <p class="error">{actionError || $lostCardStore.error}</p>
    {/if}
  </section>

  {#if isNFCModalOpen}
    <NFCModal
      on:close={() => { isNFCModalOpen = false; }}
      on:uid-read={handleUidRead}
      externalError={nfcError}
    />
  {/if}
{/if}

<style>
  .panel { display: grid; gap: 0.75rem; }
  .filters {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(220px, 1fr) repeat(2, minmax(180px, 1fr)) auto auto;
  }
  .lookup-card {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    background: var(--bg-surface-muted);
    padding: 0.75rem;
    display: grid;
    gap: 0.4rem;
  }
  .lookup-card h2 {
    margin: 0;
    font-size: 1.05rem;
  }
  .lookup-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .lookup-status {
    margin: 0;
    font-weight: 700;
  }
  .lookup-status-danger { color: #c61f35; }
  .lookup-status-warning { color: #8a5a00; }
  .lookup-status-info { color: #1f4a7c; }
  .lookup-status-muted { color: var(--text-secondary); }
  @media (max-width: 980px) {
    .filters {
      grid-template-columns: 1fr;
    }
  }
  .list { display: grid; gap: 0.5rem; }
  .row {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 0.75rem;
    display: grid;
    gap: 0.25rem;
    background: #fff;
  }
  .hint { color: var(--text-secondary); }
  .error { color: #c61f35; }
</style>
