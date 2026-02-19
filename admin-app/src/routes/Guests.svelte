<script>
  import { guestStore } from '../stores/guestStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestContextStore } from '../stores/guestContextStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { pourStore } from '../stores/pourStore.js';

  import GuestSearch from '../components/guests/GuestSearch.svelte';
  import GuestList from '../components/guests/GuestList.svelte';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import { uiStore } from '../stores/uiStore.js';

  let searchTerm = '';
  let selectedGuestId = null;
  let isModalOpen = false;
  let formError = '';
  let guestToEdit = null;
  let isNFCModalOpen = false;
  let nfcError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let initialLoadAttempted = false;

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      guestStore.fetchGuests();
      initialLoadAttempted = true;
    }
  }

  $: filteredGuests = $guestStore.guests.filter((guest) => {
    const fullName = `${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`.toLowerCase();
    return fullName.includes(searchTerm.toLowerCase());
  });

  $: selectedGuest = selectedGuestId ? $guestStore.guests.find((g) => g.guest_id === selectedGuestId) : null;
  $: guestContextStore.setGuest(selectedGuest);
  $: recentGuestPours = selectedGuest
    ? $pourStore.pours.filter((p) => p?.guest?.guest_id === selectedGuest.guest_id).slice(0, 8)
    : [];

  function handleSelectGuest(event) { selectedGuestId = event.detail.guestId; }
  function handleCloseDetail() { selectedGuestId = null; guestContextStore.clear(); }
  function handleOpenCreateModal() { guestToEdit = null; formError = ''; isModalOpen = true; }
  function handleOpenEditModal() { guestToEdit = selectedGuest; formError = ''; isModalOpen = true; }

  async function handleSave(event) {
    formError = '';
    try {
      if (guestToEdit) {
        await guestStore.updateGuest(guestToEdit.guest_id, event.detail);
      } else {
        await guestStore.createGuest(event.detail);
      }
      isModalOpen = false;
      guestToEdit = null;
    } catch (error) {
      formError = error.message || error.toString();
    }
  }

  function handleBindCard() {
    if (!selectedGuest) { uiStore.notifyWarning('Сначала выберите гостя.'); return; }
    nfcError = '';
    isNFCModalOpen = true;
  }

  async function handleUidRead(event) {
    nfcError = '';
    try {
      await guestStore.bindCardToGuest(selectedGuestId, event.detail.uid);
      uiStore.notifySuccess('Карта привязана. Можно перейти к пополнению.');
    } catch (error) {
      nfcError = error.message || error.toString();
    }
  }

  function handleOpenTopUpModal() {
    if (!selectedGuest) { uiStore.notifyWarning('Сначала выберите гостя.'); return; }
    if (!$shiftStore.isOpen) {
      uiStore.notifyWarning('Сначала откройте смену на дашборде, затем выполните пополнение.');
      return;
    }
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    topUpError = '';
    try {
      await guestStore.topUpBalance(selectedGuestId, event.detail);
      shiftStore.recordTopUp(event.detail.amount);
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Баланс пополнен на ${event.detail.amount}`);
    } catch (error) {
      topUpError = error.message || error.toString();
    }
  }
</script>

{#if !$roleStore.permissions.guests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает управление гостями.</p>
  </section>
{:else}
  <div class="guests-page-layout">
    <div class="list-panel ui-card">
      <div class="panel-header">
        <h2>Операции с гостями</h2>
        <button on:click={handleOpenCreateModal}>+ Новый гость</button>
      </div>
      <GuestSearch bind:searchTerm />
      <div class="button-group">
        <button on:click={guestStore.fetchGuests} disabled={$guestStore.loading}>
          {#if $guestStore.loading}Обновление...{:else}Обновить список{/if}
        </button>
      </div>

      {#if $guestStore.loading && $guestStore.guests.length === 0}
        <p>Загрузка гостей...</p>
      {:else if $guestStore.error}
        <p class="error">Ошибка: {$guestStore.error}</p>
      {:else if filteredGuests.length === 0}
        <p>Гостей по запросу не найдено. Создайте нового гостя для продолжения.</p>
      {:else}
        <GuestList guests={filteredGuests} on:select={handleSelectGuest} selectedId={selectedGuestId} />
      {/if}
    </div>

    <div class="detail-panel ui-card">
      {#if selectedGuest}
        <GuestDetail
          guest={selectedGuest}
          recentActivity={recentGuestPours}
          on:close={handleCloseDetail}
          on:edit={handleOpenEditModal}
          on:bind-card={handleBindCard}
          on:top-up={handleOpenTopUpModal}
        />
      {:else}
        <div class="empty-state">
          <h3>Гость не выбран</h3>
          <p>Выберите гостя слева или создайте нового, чтобы выполнить пополнение и операции по карте.</p>
          <button on:click={handleOpenCreateModal}>Создать гостя</button>
        </div>
      {/if}
    </div>
  </div>

  {#if isModalOpen}
    <Modal on:close={() => { isModalOpen = false; guestToEdit = null; }}>
      <GuestForm
        guest={guestToEdit}
        on:save={handleSave}
        on:cancel={() => { isModalOpen = false; guestToEdit = null; }}
        isSaving={$guestStore.loading}
      />
      {#if formError}<p class="error" style="margin-top: 1rem;">{formError}</p>{/if}
    </Modal>
  {/if}

  {#if isNFCModalOpen}
    <NFCModal
      on:close={() => { isNFCModalOpen = false; }}
      on:uid-read={handleUidRead}
      externalError={nfcError}
    />
  {/if}

  {#if isTopUpModalOpen}
    <TopUpModal
      guestName={`${selectedGuest.first_name} ${selectedGuest.last_name}`}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}
{/if}

<style>
  .access-denied { padding: 1rem; }
  .guests-page-layout { display: grid; grid-template-columns: minmax(320px, 420px) 1fr; gap: 1rem; min-height: 70vh; }
  .list-panel, .detail-panel { padding: 1rem; overflow-y: auto; }
  .error { color: #c61f35; }
  .panel-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
  .panel-header h2 { margin: 0; }
  .button-group { margin-bottom: 0.75rem; }
  .empty-state {
    min-height: 320px;
    display: grid;
    align-content: center;
    justify-items: start;
    gap: 0.6rem;
    padding: 1rem;
  }
  .empty-state h3 { margin: 0; }
  .empty-state p { margin: 0; color: var(--text-secondary); max-width: 520px; }
</style>
