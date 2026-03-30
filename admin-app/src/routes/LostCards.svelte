<script>
  export let embedded = false;
  import { onMount } from 'svelte';

  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { formatDateTimeRu } from '../lib/formatters.js';
  import { buildLostCardAccess } from '../lib/operator/lostCardAccess.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { ensureOperatorShellData } from '../stores/operatorShellOrchestrator.js';
  import { roleStore } from '../stores/roleStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';

  let uidFilter = '';
  let reportedFrom = '';
  let reportedTo = '';
  let actionError = '';
  let cardLookupResult = null;

  $: access = buildLostCardAccess($roleStore.permissions || {});

  function requirePermission(permissionKey, message) {
    if (permissionKey === 'cards_reissue_manage' ? access.canManage : $roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  function toIsoOrNull(value) {
    if (!value || !value.trim()) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  }

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
    if (!requirePermission('cards_reissue_manage', 'Снять отметку потери можно только ролям с перевыпуском и восстановлением карт.')) return;
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
    if (!requirePermission('cards_reissue_manage', 'Снять отметку потери можно только ролям с перевыпуском и восстановлением карт.')) return;
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
    navigateWithFocus({ target: 'visit', visitId: targetVisitId, cardUid: cardLookupResult?.card_uid });
  }

  function handleLookupOpenGuest() {
    const guestId = cardLookupResult?.guest?.guest_id || cardLookupResult?.lost_card?.guest_id;
    if (!guestId && !cardLookupResult?.card_uid) return;
    navigateWithFocus({ target: 'guest', guestId, cardUid: cardLookupResult?.card_uid });
  }

  async function handleLookupOpenNewVisit() {
    const guestId = cardLookupResult?.guest?.guest_id;
    if (!guestId) return;
    try {
      const opened = await visitStore.openVisit({ guestId });
      await Promise.allSettled([
        visitStore.fetchActiveVisits({ force: true }),
        ensureOperatorShellData({ reason: 'manual-refresh', force: true }),
      ]);
      navigateWithFocus({ target: 'visit', visitId: opened.visit_id, guestId, cardUid: cardLookupResult?.card_uid });
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Не удалось открыть новый визит';
    }
  }

  onMount(async () => {
    if (!access.canView) {
      return;
    }
    await refresh();
  });
</script>

{#if !access.canView}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с потерянными картами.</p>
  </section>
{:else}
  <section class="ui-card panel">
    <h1>{embedded ? ROUTE_COPY.lostCards.title : ROUTE_COPY.lostCards.title}</h1>
    <p class="intro">{ROUTE_COPY.lostCards.description}</p>

    <div class="filters">
      <input type="text" bind:value={uidFilter} placeholder="Поиск по UID" />
      <input type="datetime-local" bind:value={reportedFrom} />
      <input type="datetime-local" bind:value={reportedTo} />
      <button on:click={refresh} disabled={$lostCardStore.loading}>Найти</button>
    </div>

    <CardLookupPanel
      title="Проверка карты"
      description="Проверка карты по UID или NFC: потеря, гость и связанный визит в одном окне."
      result={cardLookupResult}
      error={actionError}
      loading={$lostCardStore.loading}
      allowRestoreLost={access.canManage}
      allowOpenVisit={hasLookupVisitTarget()}
      allowOpenGuest={Boolean(cardLookupResult?.guest?.guest_id || cardLookupResult?.lost_card?.guest_id || cardLookupResult?.card_uid)}
      allowOpenNewVisit={true}
      on:lookup={handleLookup}
      on:restore-lost={handleLookupRestoreLost}
      on:open-visit={handleLookupOpenVisit}
      on:open-guest={handleLookupOpenGuest}
      on:open-new-visit={handleLookupOpenNewVisit}
    />

    {#if $lostCardStore.loading}
      <p>Загрузка...</p>
    {:else if ($lostCardStore.items || []).length === 0}
      <p class="hint">Записи не найдены.</p>
    {:else}
      <div class="list">
        {#each $lostCardStore.items as item}
          <div class="row">
            <div class="row-head">
              <strong>{item.card_uid}</strong>
              <span class="status">Потеряна</span>
            </div>
            <div>Отмечена: {formatDateTimeRu(item.reported_at)}</div>
            <div>Гость: {item.guest_id || 'не указан'}</div>
            <div>Связанный визит: {item.visit_id || '—'}</div>
            <div>Причина: {item.reason || '—'}</div>
            <div>Комментарий: {item.comment || '—'}</div>
            <div class="row-actions">
              {#if access.canManage}
                <button on:click={() => onRestore(item)} disabled={$lostCardStore.loading}>Снять отметку</button>
              {/if}
              {#if item.visit_id}
                <button class="secondary" on:click={() => navigateWithFocus({ target: 'visit', visitId: item.visit_id, cardUid: item.card_uid, guestId: item.guest_id })}>Открыть визит</button>
              {/if}
              <button class="secondary" on:click={() => navigateWithFocus({ target: 'guest', guestId: item.guest_id, cardUid: item.card_uid })}>Открыть гостя</button>
            </div>
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
  .panel { display: grid; gap: 0.9rem; }
  .intro { margin: 0; color: var(--text-secondary); }
  .filters {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(220px, 1fr) repeat(2, minmax(180px, 1fr)) auto;
  }
  .list { display: grid; gap: 0.75rem; }
  .row {
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 0.9rem;
    display: grid;
    gap: 0.35rem;
    background: #fff;
  }
  .row-head, .row-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
  }
  .status {
    border-radius: 999px;
    padding: 0.3rem 0.65rem;
    background: #fff1f2;
    color: #9e1f2c;
    font-size: 0.78rem;
    font-weight: 700;
  }
  .hint { color: var(--text-secondary); }
  .error { color: #c61f35; }
  @media (max-width: 980px) {
    .filters {
      grid-template-columns: 1fr;
    }
  }
</style>
