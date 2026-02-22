<script>
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestStore } from '../stores/guestStore.js';

  let searchQuery = '';
  let forceUnlockReason = '';
  let forceUnlockComment = '';
  let closeReason = 'guest_checkout';
  let actionError = '';

  let openFlowVisible = false;
  let guestQuery = '';
  let candidateGuest = null;
  let openFlowNotFound = false;
  let openFlowError = '';

  $: visit = $visitStore.currentVisit;
  $: guest = visit ? $guestStore.guests.find((g) => g.guest_id === visit.guest_id) : null;
  $: lockActive = visit?.active_tap_id !== null && visit?.active_tap_id !== undefined;

  const fullName = (targetGuest) => {
    if (!targetGuest) return '—';
    return [targetGuest.last_name, targetGuest.first_name, targetGuest.patronymic].filter(Boolean).join(' ');
  };

  const matchesGuest = (targetGuest, query) => {
    const q = query.trim().toLowerCase();
    if (!q) return false;
    const fio = fullName(targetGuest).toLowerCase();
    const phone = (targetGuest.phone_number || '').toLowerCase();
    return fio.includes(q) || phone.includes(q);
  };

  async function ensureGuestsLoaded() {
    if ($guestStore.guests.length === 0 && !$guestStore.loading) {
      await guestStore.fetchGuests();
    }
  }

  function startOpenFlow() {
    openFlowVisible = true;
    guestQuery = '';
    candidateGuest = null;
    openFlowNotFound = false;
    openFlowError = '';
  }

  async function handleGuestSearch() {
    openFlowError = '';
    openFlowNotFound = false;
    candidateGuest = null;

    if (!guestQuery.trim()) {
      uiStore.notifyWarning('Введите ФИО или телефон гостя.');
      return;
    }

    await ensureGuestsLoaded();
    candidateGuest = $guestStore.guests.find((g) => matchesGuest(g, guestQuery)) || null;
    openFlowNotFound = !candidateGuest;
  }

  async function openVisitWithoutCard() {
    openFlowError = '';
    if (!candidateGuest) return;

    try {
      await visitStore.openVisit({ guestId: candidateGuest.guest_id });
      uiStore.notifySuccess('Визит открыт.');
    } catch (error) {
      const message = error?.message || error?.toString?.() || 'Ошибка открытия визита';
      openFlowError = message;
      if (message.includes('already has an active visit')) {
        await visitStore.searchActiveVisit(guestQuery.trim());
      }
    }
  }

  async function handleOpenExistingVisit() {
    if (!guestQuery.trim()) return;
    await visitStore.searchActiveVisit(guestQuery.trim());
  }

  async function handleSearch() {
    actionError = '';
    if (!searchQuery.trim()) {
      uiStore.notifyWarning('Введите строку поиска.');
      return;
    }

    try {
      await visitStore.searchActiveVisit(searchQuery.trim());
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка поиска визита';
    }
  }

  async function handleForceUnlock() {
    actionError = '';
    if (!visit) return;
    if (!forceUnlockReason.trim()) {
      uiStore.notifyWarning('Reason обязателен для Force Unlock.');
      return;
    }

    try {
      await visitStore.forceUnlock({
        visitId: visit.visit_id,
        reason: forceUnlockReason.trim(),
        comment: forceUnlockComment.trim() || null,
      });
      uiStore.notifySuccess('Force unlock выполнен.');
      forceUnlockReason = '';
      forceUnlockComment = '';
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка force unlock';
    }
  }

  async function handleCloseVisit() {
    actionError = '';
    if (!visit) return;

    try {
      await visitStore.closeVisit({
        visitId: visit.visit_id,
        closedReason: closeReason,
        cardReturned: true,
      });
      uiStore.notifySuccess('Визит закрыт.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Ошибка закрытия визита';
    }
  }
</script>

{#if !$roleStore.permissions.guests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с визитами.</p>
  </section>
{:else}
  <section class="search-card ui-card">
    <h1>Визиты</h1>
    <button class="primary-open" on:click={startOpenFlow}>Открыть новый визит</button>

    {#if openFlowVisible}
      <div class="open-flow">
        <h2>Open Visit Flow</h2>
        <p class="hint">Найдите гостя по ФИО или телефону.</p>
        <div class="search-row">
          <input
            type="text"
            bind:value={guestQuery}
            placeholder="ФИО / телефон"
            on:keydown={(e) => e.key === 'Enter' && handleGuestSearch()}
          />
          <button on:click={handleGuestSearch} disabled={$guestStore.loading || $visitStore.loading}>Найти гостя</button>
        </div>

        {#if openFlowNotFound}
          <p class="not-found">Гость не найден</p>
        {/if}

        {#if candidateGuest}
          <div class="candidate-card">
            <div><strong>ФИО:</strong> {fullName(candidateGuest)}</div>
            <div><strong>Телефон:</strong> {candidateGuest.phone_number}</div>
            <div><strong>Баланс:</strong> {candidateGuest.balance}</div>
          </div>
          <div class="open-actions">
            <button on:click={openVisitWithoutCard} disabled={$visitStore.loading}>Открыть визит без карты</button>
            <button disabled title="Будет добавлено отдельным этапом">Открыть визит и выдать карту</button>
          </div>
        {/if}

        {#if openFlowError}
          <p class="error">{openFlowError}</p>
          {#if openFlowError.includes('already has an active visit')}
            <button on:click={handleOpenExistingVisit}>Открыть существующий визит</button>
          {/if}
        {/if}
      </div>
    {/if}
  </section>

  <section class="search-card ui-card">
    <h2>Active Visit Search</h2>
    <div class="search-row">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Card UID / phone / full name"
        on:keydown={(e) => e.key === 'Enter' && handleSearch()}
      />
      <button on:click={handleSearch} disabled={$visitStore.loading}>Search</button>
    </div>

    {#if $visitStore.notFound}
      <p class="not-found">Active visit not found</p>
    {/if}
    {#if actionError || $visitStore.error}
      <p class="error">{actionError || $visitStore.error}</p>
    {/if}
  </section>

  {#if visit}
    <section class="visit-card ui-card">
      <h2>Visit Card</h2>

      <div class="visit-fields">
        <div><strong>Guest:</strong> {fullName(guest)}</div>
        <div><strong>Phone:</strong> {guest?.phone_number || '—'}</div>
        <div><strong>Card UID:</strong> {visit.card_uid || '—'}</div>
        <div><strong>Visit status:</strong> {visit.status}</div>
        <div><strong>Balance:</strong> {guest?.balance ?? '—'}</div>
      </div>

      <div class="lock-state" class:locked={lockActive} class:free={!lockActive}>
        {#if lockActive}
          <strong>Locked on tap #{visit.active_tap_id}</strong>
        {:else}
          <strong>No active tap</strong>
        {/if}
      </div>

      <div class="actions-grid">
        <div class="action-panel">
          <h3>Force Unlock</h3>
          <input type="text" bind:value={forceUnlockReason} placeholder="Reason (required)" />
          <textarea bind:value={forceUnlockComment} rows="2" placeholder="Comment (optional)"></textarea>
          <button on:click={handleForceUnlock} disabled={$visitStore.loading || !lockActive}>Force Unlock</button>
        </div>

        <div class="action-panel">
          <h3>Close Visit</h3>
          <input type="text" bind:value={closeReason} placeholder="Close reason" />
          <button on:click={handleCloseVisit} disabled={$visitStore.loading || visit.status !== 'active'}>Close Visit</button>
        </div>

        <div class="action-panel">
          <h3>Top-up</h3>
          <button disabled title="Visit-centric top-up coming later">Top-up (coming soon)</button>
        </div>
      </div>
    </section>
  {/if}
{/if}

<style>
  .search-card { margin-bottom: 1rem; }
  .hint { margin-top: 0; color: var(--text-secondary); }
  .search-row { display: flex; gap: 0.75rem; }
  .search-row input { flex: 1; }
  .primary-open { margin-bottom: 0.75rem; }

  .open-flow {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    background: var(--bg-surface-muted);
    padding: 0.75rem;
    display: grid;
    gap: 0.75rem;
  }
  .open-flow h2 { margin: 0; }
  .candidate-card {
    border: 1px solid var(--border-soft);
    background: #fff;
    border-radius: 8px;
    padding: 0.6rem;
    display: grid;
    gap: 0.25rem;
  }
  .open-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }

  .visit-card { display: grid; gap: 1rem; }
  .visit-fields { display: grid; gap: 0.4rem; }

  .lock-state {
    border-radius: 10px;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border-soft);
  }

  .lock-state.locked {
    background: #fff3cd;
    border-color: #f0ad4e;
    color: #8a5a00;
  }

  .lock-state.free {
    background: #e9f7ef;
    border-color: #7bc697;
    color: #1f6b3d;
  }

  .actions-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

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
</style>
