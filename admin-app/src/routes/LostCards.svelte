<script>
  import { onMount } from 'svelte';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';

  let uidFilter = '';
  let reportedFrom = '';
  let reportedTo = '';
  let actionError = '';

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
    </div>

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
{/if}

<style>
  .panel { display: grid; gap: 0.75rem; }
  .filters {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(220px, 1fr) repeat(2, minmax(180px, 1fr)) auto;
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
