<script>
  import { onMount } from 'svelte';

  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { formatCardStatus, formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../lib/formatters.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { normalizeError } from '../lib/errorUtils.js';
  import { guestStore } from '../stores/guestStore.js';
  import { ensureOperatorShellData } from '../stores/operatorShellOrchestrator.js';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';

  let searchTerm = '';
  let selectedGuestId = '';
  let initialLoadAttempted = false;
  let isGuestModalOpen = false;
  let guestToEdit = null;
  let formError = '';
  let isNfcModalOpen = false;
  let nfcError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let pendingOpenGuest = null;

  function fullName(guest) {
    return [guest?.last_name, guest?.first_name, guest?.patronymic].filter(Boolean).join(' ') || 'Гость без имени';
  }

  function matchesGuest(guest, query) {
    const normalized = String(query || '').trim().toLowerCase();
    if (!normalized) return true;
    return [
      fullName(guest),
      guest?.phone_number,
      ...(Array.isArray(guest?.cards) ? guest.cards.map((card) => card.card_uid) : []),
    ].some((value) => String(value || '').toLowerCase().includes(normalized));
  }

  $: if ($sessionStore.token && !initialLoadAttempted) {
    guestStore.fetchGuests();
    visitStore.fetchActiveVisits();
    initialLoadAttempted = true;
  }

  $: filteredGuests = ($guestStore.guests || []).filter((guest) => matchesGuest(guest, searchTerm));
  $: if (filteredGuests.length && !filteredGuests.some((guest) => String(guest.guest_id) === String(selectedGuestId))) {
    selectedGuestId = filteredGuests[0].guest_id;
  } else if (!filteredGuests.length && selectedGuestId) {
    selectedGuestId = '';
  }
  $: selectedGuest = ($guestStore.guests || []).find((guest) => String(guest.guest_id) === String(selectedGuestId)) || null;
  $: activeVisit = selectedGuest ? ($visitStore.activeVisits || []).find((visit) => visit.guest_id === selectedGuest.guest_id) : null;
  $: primaryCard = activeVisit
    ? {
      card_uid: activeVisit.card_uid,
      status: activeVisit.operational_status === 'active_blocked_lost_card' ? 'lost' : 'assigned_to_visit',
    }
    : null;
  $: recentPours = (selectedGuest?.pours || []).slice().sort((left, right) => new Date(right.poured_at).getTime() - new Date(left.poured_at).getTime()).slice(0, 5);
  $: recentTransactions = (selectedGuest?.transactions || []).slice().sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()).slice(0, 4);

  onMount(() => {
    const focusGuestId = sessionStorage.getItem('guests.focusGuestId');
    if (focusGuestId) {
      selectedGuestId = focusGuestId;
      sessionStorage.removeItem('guests.focusGuestId');
    }
    const focusCardUid = sessionStorage.getItem('guests.focusCardUid');
    if (focusCardUid) {
      searchTerm = focusCardUid;
      sessionStorage.removeItem('guests.focusCardUid');
    }
  });

  function openCreateModal() {
    guestToEdit = null;
    formError = '';
    isGuestModalOpen = true;
  }

  function openEditModal() {
    guestToEdit = selectedGuest;
    formError = '';
    isGuestModalOpen = true;
  }

  async function handleSaveGuest(event) {
    formError = '';
    try {
      if (guestToEdit) {
        await guestStore.updateGuest(guestToEdit.guest_id, event.detail);
      } else {
        await guestStore.createGuest(event.detail);
      }
      await guestStore.fetchGuests({ force: true });
      isGuestModalOpen = false;
      guestToEdit = null;
    } catch (error) {
      formError = normalizeError(error);
    }
  }

  async function handleUidRead(event) {
    nfcError = '';
    if (!pendingOpenGuest?.guest_id) {
      nfcError = 'Этот NFC scan path используется для открытия визита с выдачей карты.';
      return;
    }
    try {
      const opened = await visitStore.openVisit({ guestId: pendingOpenGuest.guest_id, cardUid: event.detail.uid });
      await Promise.allSettled([
        visitStore.fetchActiveVisits({ force: true }),
        guestStore.fetchGuests({ force: true }),
        ensureOperatorShellData({ reason: 'manual-refresh', force: true }),
      ]);
      pendingOpenGuest = null;
      isNfcModalOpen = false;
      uiStore.notifySuccess('Визит открыт. Если карта была новой, система автоматически добавила её в пул.');
      navigateWithFocus({ target: 'visit', visitId: opened.visit_id, guestId: opened.guest_id, cardUid: opened.card_uid });
    } catch (error) {
      nfcError = normalizeError(error);
    }
  }

  function handleOpenTopUp() {
    if (!selectedGuest) return;
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    topUpError = '';
    try {
      await guestStore.topUpBalance(selectedGuest.guest_id, event.detail);
      await guestStore.fetchGuests({ force: true });
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Баланс пополнен на ${formatRubAmount(event.detail.amount)}`);
    } catch (error) {
      topUpError = normalizeError(error);
    }
  }

  async function handleOpenVisit() {
    if (!selectedGuest) return;
    if (activeVisit?.visit_id) {
      navigateWithFocus({ target: 'visit', visitId: activeVisit.visit_id, guestId: selectedGuest.guest_id, cardUid: primaryCard?.card_uid });
      return;
    }
    pendingOpenGuest = selectedGuest;
    nfcError = '';
    isNfcModalOpen = true;
  }

  function guestCardLabel(guest) {
    const visit = ($visitStore.activeVisits || []).find((item) => item.guest_id === guest.guest_id);
    return visit?.card_uid || 'Нет активного визита';
  }
</script>

{#if !($roleStore.permissions.cards_lookup || $roleStore.permissions.cards_reissue_manage || $roleStore.permissions.sessions_view)}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает работу с гостями.</p>
  </section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>{ROUTE_COPY.guests.title}</h1>
        <p>{ROUTE_COPY.guests.description}</p>
      </div>
      <button on:click={openCreateModal}>Новый гость</button>
    </div>

    <div class="content-grid">
      <section class="ui-card list-panel">
        <div class="search-row">
          <input bind:value={searchTerm} placeholder="Поиск по имени, телефону или карте" />
          <button class="secondary" on:click={() => guestStore.fetchGuests({ force: true })} disabled={$guestStore.loading}>Обновить</button>
        </div>

        {#if $guestStore.loading && ($guestStore.guests || []).length === 0}
          <p>Загрузка гостей...</p>
        {:else if $guestStore.error}
          <p class="error">{$guestStore.error}</p>
        {:else if filteredGuests.length === 0}
          <p class="muted">Гости по запросу не найдены.</p>
        {:else}
          <div class="guest-list">
            {#each filteredGuests as guest}
              <button class:selected={guest.guest_id === selectedGuestId} class="guest-item" on:click={() => (selectedGuestId = guest.guest_id)}>
                <div class="row top">
                  <strong>{fullName(guest)}</strong>
                  <span class:active={Boolean(($visitStore.activeVisits || []).find((visit) => visit.guest_id === guest.guest_id))} class="visit-flag">
                    {#if ($visitStore.activeVisits || []).find((visit) => visit.guest_id === guest.guest_id)}
                      Активный визит
                    {:else}
                      История
                    {/if}
                  </span>
                </div>
                <div class="row meta"><span>{guest.phone_number}</span><span>{guestCardLabel(guest)}</span></div>
                <div class="row meta"><span>Баланс: {formatRubAmount(guest.balance)}</span><span>{guest.is_active ? 'Активен' : 'Заблокирован'}</span></div>
              </button>
            {/each}
          </div>
        {/if}
      </section>

      <section class="ui-card detail-panel">
        {#if selectedGuest}
          <div class="detail-head">
            <div>
              <h2>{fullName(selectedGuest)}</h2>
              <p>{selectedGuest.phone_number || 'Телефон не указан'}</p>
            </div>
            <button class="secondary" on:click={openEditModal}>Редактировать</button>
          </div>

          <div class="summary-grid">
            <article>
              <span>Карта</span>
              <strong>{primaryCard?.card_uid || 'Нет активного визита'}</strong>
              <small>{primaryCard ? formatCardStatus(primaryCard.status) : 'Карта выдаётся только при открытии активного визита'}</small>
            </article>
            <article>
              <span>Баланс</span>
              <strong>{formatRubAmount(selectedGuest.balance)}</strong>
              <small>{selectedGuest.is_active ? 'Гость активен' : 'Гость заблокирован'}</small>
            </article>
            <article>
              <span>Активный визит</span>
              <strong>{activeVisit?.visit_id || 'Нет активного визита'}</strong>
              <small>{activeVisit?.active_tap_id ? `Кран #${activeVisit.active_tap_id}` : 'Кран не выбран'}</small>
            </article>
            <article>
              <span>Создан</span>
              <strong>{formatDateTimeRu(selectedGuest.created_at)}</strong>
              <small>Последнее обновление: {formatDateTimeRu(selectedGuest.updated_at)}</small>
            </article>
          </div>

          <div class="action-row">
            <button on:click={handleOpenVisit}>{activeVisit?.visit_id ? 'Продолжить визит' : 'Выдать карту и открыть визит'}</button>
            <button class="secondary" on:click={handleOpenTopUp}>Пополнить</button>
            <button class="secondary" on:click={() => (window.location.hash = '/lost-cards')}>Потерянная карта</button>
          </div>

          <section class="detail-section">
            <h3>Последние наливы</h3>
            {#if recentPours.length === 0}
              <p class="muted">У гостя пока нет недавних наливов.</p>
            {:else}
              <div class="event-list">
                {#each recentPours as pour}
                  <button class="event-row" on:click={() => navigateWithFocus({ target: 'pour', route: '/pours', pourRef: `pour:${pour.pour_id}`, guestId: selectedGuest.guest_id, visitId: pour.visit_id, tapId: pour.tap_id })}>
                    <div>
                      <strong>{pour.beverage?.name || 'Налив'}</strong>
                      <p>{pour.tap?.display_name || `Кран #${pour.tap_id || '—'}`} · {formatVolumeRu(pour.volume_ml)}</p>
                    </div>
                    <small>{formatDateTimeRu(pour.poured_at)}</small>
                  </button>
                {/each}
              </div>
            {/if}
          </section>

          <section class="detail-section">
            <h3>Последние пополнения и операции</h3>
            {#if recentTransactions.length === 0}
              <p class="muted">У гостя пока нет недавних транзакций.</p>
            {:else}
              <div class="event-list">
                {#each recentTransactions as tx}
                  <div class="event-row static">
                    <div>
                      <strong>{tx.type || 'Операция'}</strong>
                      <p>{formatRubAmount(tx.amount || 0)}</p>
                    </div>
                    <small>{formatDateTimeRu(tx.created_at)}</small>
                  </div>
                {/each}
              </div>
            {/if}
          </section>
        {:else}
          <div class="empty-state">
            <h2>Гость не выбран</h2>
            <p>Выберите гостя слева или создайте нового, чтобы перейти к карте, балансу и активному визиту.</p>
          </div>
        {/if}
      </section>
    </div>
  </section>

  {#if isGuestModalOpen}
    <Modal on:close={() => { isGuestModalOpen = false; guestToEdit = null; }}>
      <GuestForm
        guest={guestToEdit}
        on:save={handleSaveGuest}
        on:cancel={() => { isGuestModalOpen = false; guestToEdit = null; }}
        isSaving={$guestStore.loading}
      />
      {#if formError}<p class="error">{formError}</p>{/if}
    </Modal>
  {/if}

  {#if isNfcModalOpen}
    <NFCModal
      on:close={() => { isNfcModalOpen = false; pendingOpenGuest = null; }}
      on:uid-read={handleUidRead}
      externalError={nfcError}
    />
  {/if}

  {#if isTopUpModalOpen && selectedGuest}
    <TopUpModal
      guestName={fullName(selectedGuest)}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}
{/if}

<style>
  .page, .list-panel, .detail-panel, .detail-section { display: grid; gap: 0.85rem; }
  .page-header, .search-row, .detail-head, .row, .action-row { display: flex; gap: 0.75rem; justify-content: space-between; align-items: flex-start; }
  .page-header p, .detail-head p, .muted { margin: 0.25rem 0 0; color: var(--text-secondary); }
  .content-grid { display: grid; gap: 0.9rem; grid-template-columns: minmax(300px, 390px) minmax(0, 1fr); align-items: start; }
  .search-row { align-items: center; }
  .search-row input { flex: 1 1 auto; }
  .guest-list, .event-list { display: grid; gap: 0.65rem; }
  .guest-item, .event-row {
    text-align: left;
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    padding: 0.8rem;
    background: #fff;
    color: inherit;
    display: grid;
    gap: 0.4rem;
  }
  .guest-item.selected { border-color: #2563eb; box-shadow: 0 0 0 1px #bfdbfe; }
  .visit-flag {
    padding: 0.3rem 0.65rem;
    border-radius: 999px;
    background: var(--bg-surface-muted);
    color: var(--text-secondary);
    font-size: 0.78rem;
    font-weight: 700;
  }
  .visit-flag.active {
    background: #eef2ff;
    color: #3447a3;
  }
  .meta { color: var(--text-secondary); flex-wrap: wrap; }
  .summary-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .summary-grid article {
    display: grid;
    gap: 0.25rem;
    padding: 0.8rem;
    border-radius: 14px;
    background: var(--bg-surface-muted);
  }
  .summary-grid span, .summary-grid small { color: var(--text-secondary); }
  .action-row { flex-wrap: wrap; }
  .event-row { grid-template-columns: minmax(0, 1fr) auto; align-items: start; }
  .event-row.static { cursor: default; }
  .event-row p { margin: 0.2rem 0 0; color: var(--text-secondary); }
  .error { color: var(--state-critical-text); }
  @media (max-width: 1100px) {
    .content-grid, .summary-grid { grid-template-columns: 1fr; }
    .page-header, .search-row, .detail-head, .row, .action-row, .event-row { flex-direction: column; align-items: stretch; }
    .event-row { display: grid; grid-template-columns: 1fr; }
  }
</style>
