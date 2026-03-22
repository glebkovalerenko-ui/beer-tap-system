<script>
  export let embedded = false;
  import { onMount } from 'svelte';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import { formatDateTimeRu } from '../lib/formatters.js';

  let uidFilter = '';
  let reportedFrom = '';
  let reportedTo = '';
  let actionError = '';
  let cardLookupResult = null;

  function requirePermission(permissionKey, message) {
    if ($roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  const toIsoOrNull = (value) => {
    if (!value || !value.trim()) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
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
    if (!requirePermission('cards_manage', 'Снятие отметки LostCard доступно только ролям с управлением картами.')) return;
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

  async function handleLookup(event) {
    try {
      await resolveByCardUid(event.detail.uid);
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось выполнить поиск по карте';
    }
  }

  async function handleLookupRestoreLost() {
    if (!requirePermission('cards_manage', 'Снятие отметки LostCard доступно только ролям с управлением картами.')) return;
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
    window.location.hash = '/sessions';
  }

  async function handleLookupOpenNewVisit() {
    const guestId = cardLookupResult?.guest?.guest_id;
    if (!guestId) return;
    try {
      const opened = await visitStore.openVisit({ guestId });
      sessionStorage.setItem('visits.lookupVisitId', opened.visit_id);
      window.location.hash = '/sessions';
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось открыть новый визит';
    }
  }

  onMount(async () => {
    await refresh();
  });
</script>

{#if !$roleStore.permissions.cards_manage}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с потерянными картами.</p>
  </section>
{:else}
  <section class="ui-card panel">
    <h1>{embedded ? 'Потерянные карты' : 'Инциденты по картам'}</h1>

    <div class="filters">
      <input type="text" bind:value={uidFilter} placeholder="Поиск по UID" />
      <input type="datetime-local" bind:value={reportedFrom} />
      <input type="datetime-local" bind:value={reportedTo} />
      <button on:click={refresh} disabled={$lostCardStore.loading}>Найти</button>
    </div>

    <CardLookupPanel
      title="Проверка статуса карты"
      description="Переиспользуемый lookup по NFC или UID для lost-карт и текущего визита."
      result={cardLookupResult}
      error={actionError}
      loading={$lostCardStore.loading}
      allowRestoreLost={$roleStore.permissions.cards_manage}
      allowOpenVisit={hasLookupVisitTarget()}
      allowOpenGuest={false}
      allowOpenNewVisit={true}
      on:lookup={handleLookup}
      on:restore-lost={handleLookupRestoreLost}
      on:open-visit={handleLookupOpenVisit}
      on:open-new-visit={handleLookupOpenNewVisit}
    />

    {#if $lostCardStore.loading}
      <p>Загрузка...</p>
    {:else if ($lostCardStore.items || []).length === 0}
      <p class="hint">Записи не найдены</p>
    {:else}
      <div class="list">
        {#each $lostCardStore.items as item}
          <div class="row">
            <div><strong>{item.card_uid}</strong></div>
            <div>Дата отметки: {formatDateTimeRu(item.reported_at)}</div>
            <div>Причина: {item.reason || '—'}</div>
            <div>Комментарий: {item.comment || '—'}</div>
            <div>ID визита: {item.visit_id || '—'}</div>
            <button on:click={() => onRestore(item)} disabled={$lostCardStore.loading}>Снять отметку</button>
          </div>
        {/each}
      </div>
    {/if}

    {#if actionError || $lostCardStore.error}
      <p class="error">{actionError || $lostCardStore.error}</p>
    {/if}
  </section>

{/if}

<style>
  .panel { display: grid; gap: 0.75rem; }
  .filters {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(220px, 1fr) repeat(2, minmax(180px, 1fr)) auto;
  }
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
