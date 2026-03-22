<script>
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { guestStore } from '../stores/guestStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { normalizeError } from '../lib/errorUtils.js';
  import { formatDateTimeRu, formatRubAmount } from '../lib/formatters.js';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';

  let phoneQuery = '';
  let selectedGuestId = null;
  let selectedLookup = null;
  let lookupError = '';
  let pageError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let isEditModalOpen = false;
  let formError = '';
  let initialLoadAttempted = false;

  const fullName = (guest) => [guest?.last_name, guest?.first_name, guest?.patronymic].filter(Boolean).join(' ');

  $: {
    if (!initialLoadAttempted) {
      guestStore.fetchGuests();
      visitStore.fetchActiveVisits();
      initialLoadAttempted = true;
    }
  }

  $: guests = $guestStore.guests || [];
  $: activeVisits = $visitStore.activeVisits || [];
  $: phoneCandidates = guests.filter((guest) => {
    const q = phoneQuery.trim().toLowerCase();
    if (!q) return false;
    return (guest.phone_number || '').toLowerCase().includes(q);
  }).slice(0, 12);
  $: selectedGuest = selectedGuestId ? guests.find((guest) => guest.guest_id === selectedGuestId) : null;
  $: selectedGuest = !selectedGuest && selectedLookup?.guest?.guest_id
    ? guests.find((guest) => guest.guest_id === selectedLookup.guest.guest_id) || null
    : selectedGuest;
  $: selectedVisit = selectedGuest ? activeVisits.find((visit) => visit.guest_id === selectedGuest.guest_id) || null : null;
  $: recentGuestPours = selectedGuest
    ? $pourStore.pours.filter((item) => item?.guest?.guest_id === selectedGuest.guest_id).slice(0, 6)
    : [];
  $: lastTapLabel = recentGuestPours[0]?.tap?.display_name || (recentGuestPours[0]?.tap_id ? `Кран #${recentGuestPours[0].tap_id}` : '—');
  $: recentEvents = buildRecentEvents(selectedGuest, selectedVisit, selectedLookup, recentGuestPours);

  function buildRecentEvents(guest, visit, lookup, pours) {
    if (!guest) return [];
    const items = [];
    if (lookup?.is_lost) {
      items.push({ title: 'Карта в статусе lost', description: lookup.lost_card?.comment || 'Нужна проверка и перевыпуск карты.', timestamp: lookup.lost_card?.reported_at });
    }
    if (visit) {
      items.push({ title: 'Активный визит открыт', description: visit.active_tap_id ? `Сейчас есть лок на кране #${visit.active_tap_id}.` : 'Визит активен, локов сейчас нет.', timestamp: visit.opened_at || visit.updated_at });
    }
    for (const pour of pours.slice(0, 4)) {
      items.push({
        title: `Налив ${pour.beverage?.name || ''}`.trim(),
        description: `${pour.tap?.display_name || `Кран #${pour.tap_id || '—'}`} · ${formatRubAmount(pour.amount_charged || 0)}`,
        timestamp: pour.poured_at,
      });
    }
    for (const tx of (guest.transactions || []).slice(0, 3)) {
      items.push({
        title: tx.type || 'Операция по балансу',
        description: `${formatRubAmount(tx.amount || 0)}`,
        timestamp: tx.created_at,
      });
    }
    return items.filter((item) => item.timestamp).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 6);
  }

  function selectGuest(guestId) {
    selectedGuestId = guestId;
    pageError = '';
  }

  async function handleLookup(event) {
    lookupError = '';
    pageError = '';
    try {
      selectedLookup = await lostCardStore.resolveCard(event.detail.uid);
      if (selectedLookup?.guest?.guest_id) {
        selectedGuestId = selectedLookup.guest.guest_id;
      }
      await visitStore.fetchActiveVisits();
    } catch (error) {
      lookupError = normalizeError(error);
      selectedLookup = null;
    }
  }

  async function handleRestoreLost(event) {
    const uid = event.detail.uid;
    if (!uid) return;
    try {
      await lostCardStore.restoreLostCard(uid);
      selectedLookup = await lostCardStore.resolveCard(uid);
      uiStore.notifySuccess('Отметка lost снята');
    } catch (error) {
      lookupError = normalizeError(error);
    }
  }

  function handleOpenVisit() {
    const visitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id;
    if (!visitId) return;
    sessionStorage.setItem('visits.lookupVisitId', visitId);
    window.location.hash = '/sessions';
  }

  function handleOpenHistory() {
    const cardUid = selectedLookup?.card_uid || selectedGuest?.cards?.[0]?.card_uid || '';
    if (cardUid) sessionStorage.setItem('sessions.history.cardUid', cardUid);
    window.location.hash = '/sessions/history';
  }

  async function handleOpenNewVisit(event) {
    try {
      const opened = await visitStore.openVisit({ guestId: event.detail.guestId });
      sessionStorage.setItem('visits.lookupVisitId', opened.visit_id);
      await visitStore.fetchActiveVisits();
      uiStore.notifySuccess('Открыт новый визит');
    } catch (error) {
      lookupError = normalizeError(error);
    }
  }

  function handleOpenTopUpModal() {
    if (!selectedGuest) return;
    if (!get(shiftStore).isOpen) {
      uiStore.notifyWarning('Сначала откройте смену на дашборде, затем выполните пополнение.');
      return;
    }
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
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
    const visitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id;
    if (!visitId) {
      uiStore.notifyWarning('Пометить lost можно из активного визита с привязанной картой.');
      return;
    }
    try {
      await visitStore.reportLostCard({ visitId, reason: 'operator_marked_lost', comment: null });
      const uid = selectedLookup?.card_uid || selectedGuest?.cards?.[0]?.card_uid;
      if (uid) selectedLookup = await lostCardStore.resolveCard(uid);
      await visitStore.fetchActiveVisits();
      uiStore.notifySuccess('Карта помечена как lost');
    } catch (error) {
      pageError = normalizeError(error);
    }
  }

  async function handleSaveGuest(event) {
    formError = '';
    try {
      await guestStore.updateGuest(selectedGuest.guest_id, event.detail);
      isEditModalOpen = false;
      uiStore.notifySuccess('Данные гостя обновлены');
    } catch (error) {
      formError = normalizeError(error);
    }
  }

  onMount(async () => {
    await Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()]);
  });
</script>

{#if !$roleStore.permissions.cards_manage}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает операции с картами и гостями.</p>
  </section>
{:else}
  <section class="cards-guests-page">
    <header class="page-header ui-card">
      <div>
        <h1>Карты и гости</h1>
        <p>Единый операторский экран для быстрого входа: приложите карту, введите UID или найдите гостя по номеру телефона.</p>
      </div>
      <div class="header-actions">
        <button on:click={() => Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()])} disabled={$guestStore.loading || $visitStore.loading}>Обновить данные</button>
      </div>
    </header>

    <div class="quick-grid">
      <CardLookupPanel
        title="Главный быстрый вход"
        description="Приложите карту на NFC, введите UID вручную или используйте поиск по номеру справа."
        result={selectedLookup}
        error={lookupError}
        loading={$lostCardStore.loading || $visitStore.loading}
        allowRestoreLost={$roleStore.permissions.cards_manage}
        allowOpenVisit={true}
        allowOpenGuest={true}
        allowOpenNewVisit={true}
        openVisitLabel="Открыть активную сессию"
        openGuestLabel="Открыть гостя"
        openNewVisitLabel="Открыть новый визит"
        on:lookup={handleLookup}
        on:restore-lost={handleRestoreLost}
        on:open-visit={handleOpenVisit}
        on:open-guest={(event) => selectGuest(event.detail.guestId)}
        on:open-new-visit={handleOpenNewVisit}
      />

      <section class="ui-card phone-panel">
        <div class="section-top">
          <div>
            <h2>Найти по номеру</h2>
            <p>Введите часть телефона, чтобы быстро открыть карточку гостя.</p>
          </div>
        </div>
        <input type="text" bind:value={phoneQuery} placeholder="+7 / последние цифры телефона" />

        {#if phoneQuery.trim() && phoneCandidates.length === 0}
          <p class="hint">По номеру ничего не найдено.</p>
        {:else if phoneCandidates.length > 0}
          <div class="phone-list">
            {#each phoneCandidates as guest}
              <button class:selected={selectedGuest?.guest_id === guest.guest_id} class="phone-item" on:click={() => selectGuest(guest.guest_id)}>
                <div>
                  <strong>{fullName(guest)}</strong>
                  <div>{guest.phone_number}</div>
                </div>
                <div>
                  <strong>{formatRubAmount(guest.balance)}</strong>
                  <div>{activeVisits.some((visit) => visit.guest_id === guest.guest_id) ? 'Есть активный визит' : 'Без активного визита'}</div>
                </div>
              </button>
            {/each}
          </div>
        {:else}
          <p class="hint">Поиск по телефону покажет здесь до 12 совпадений.</p>
        {/if}
      </section>
    </div>

    <section class="ui-card detail-panel">
      {#if selectedGuest}
        <GuestDetail
          guest={selectedGuest}
          activeVisit={selectedVisit}
          cardLookup={selectedLookup}
          recentActivity={recentGuestPours}
          recentEvents={recentEvents}
          lastTapLabel={lastTapLabel}
          on:close={() => { selectedGuestId = null; selectedLookup = null; phoneQuery = ''; }}
          on:top-up={handleOpenTopUpModal}
          on:toggle-block={handleToggleBlock}
          on:mark-lost={handleMarkLost}
          on:open-history={handleOpenHistory}
          on:open-visit={handleOpenVisit}
          on:edit={() => { formError = ''; isEditModalOpen = true; }}
        />
      {:else}
        <div class="empty-state">
          <h3>Быстрый вход ждёт действие</h3>
          <p>Сначала приложите карту, введите UID или найдите гостя по номеру телефона. После выбора здесь откроется операторская карточка.</p>
        </div>
      {/if}

      {#if pageError || $guestStore.error || $visitStore.error}
        <p class="error">{pageError || $guestStore.error || $visitStore.error}</p>
      {/if}
    </section>

    {#if selectedLookup?.is_lost}
      <section class="ui-card incident-strip">
        <strong>Карта в статусе lost.</strong>
        <span>Отмечена {formatDateTimeRu(selectedLookup.lost_card?.reported_at)}. Проверьте гостя и при необходимости снимите отметку прямо из быстрого входа.</span>
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

  {#if isEditModalOpen && selectedGuest}
    <Modal on:close={() => { isEditModalOpen = false; }}>
      <GuestForm guest={selectedGuest} on:save={handleSaveGuest} on:cancel={() => { isEditModalOpen = false; }} isSaving={$guestStore.loading} />
      {#if formError}<p class="error">{formError}</p>{/if}
    </Modal>
  {/if}
{/if}

<style>
  .cards-guests-page { display: grid; gap: 1rem; }
  .page-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; }
  .page-header h1, .page-header p { margin: 0; }
  .page-header p, .hint { color: var(--text-secondary); }
  .quick-grid { display: grid; gap: 1rem; grid-template-columns: minmax(420px, 1.3fr) minmax(320px, 0.9fr); }
  .phone-panel, .detail-panel { display: grid; gap: 0.8rem; }
  .section-top h2, .section-top p { margin: 0; }
  .phone-list { display: grid; gap: 0.6rem; }
  .phone-item {
    width: 100%; display: flex; justify-content: space-between; gap: 1rem; text-align: left;
    border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; padding: 0.85rem;
  }
  .phone-item.selected { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12); }
  .empty-state { min-height: 280px; display: grid; align-content: center; gap: 0.5rem; }
  .empty-state h3, .empty-state p { margin: 0; }
  .incident-strip { display: flex; gap: 0.75rem; align-items: center; background: #fff7ed; border-color: #fed7aa; }
  .error { color: #c61f35; margin: 0; }
  @media (max-width: 1024px) {
    .quick-grid { grid-template-columns: 1fr; }
    .page-header { flex-direction: column; align-items: start; }
  }
</style>
