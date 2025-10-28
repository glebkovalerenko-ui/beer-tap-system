<!-- src/routes/Guests.svelte -->

<script>
  // --- ИЗМЕНЕНИЕ: onMount больше не нужен для загрузки, убираем его из импорта ---
  import { guestStore } from '../stores/guestStore.js';
  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Импортируем sessionStore, чтобы следить за токеном +++
  import { sessionStore } from '../stores/sessionStore.js';
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++

  import GuestSearch from '../components/guests/GuestSearch.svelte';
  import GuestList from '../components/guests/GuestList.svelte';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';

  // --- Управление состоянием (без изменений) ---
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
  // Мы запускаем загрузку, только если:
  // 1. Токен появился (мы аутентифицированы).
  // 2. И мы еще НЕ ПЫТАЛИСЬ выполнить первоначальную загрузку.
  if ($sessionStore.token && !initialLoadAttempted) {
    console.log("Токен доступен, первая попытка загрузки гостей...");
    guestStore.fetchGuests();
    initialLoadAttempted = true; // <-- Устанавливаем флаг, что попытка была.
  }
}

  // --- Производные данные (без изменений) ---
  $: filteredGuests = $guestStore.guests.filter(guest => {
    const fullName = `${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`.toLowerCase();
    return fullName.includes(searchTerm.toLowerCase());
  });

  $: selectedGuest = selectedGuestId 
    ? $guestStore.guests.find(g => g.guest_id === selectedGuestId) 
    : null;

  // --- Обработчики событий (остаются без изменений) ---
  function handleSelectGuest(event) { selectedGuestId = event.detail.guestId; }
  function handleCloseDetail() { selectedGuestId = null; }
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
    if (!selectedGuest) { alert("Please select a guest first."); return; }
    nfcError = ''; 
    isNFCModalOpen = true;
  }

  async function handleUidRead(event) {
    const uid = event.detail.uid;
    console.log(`✅ UID ${uid} получен. Привязываем к гостю ID: ${selectedGuestId}`);
    nfcError = ''; 
    try {
      await guestStore.bindCardToGuest(selectedGuestId, uid);
    } catch (error) {
      const errorMessage = error.message || error.toString();
      console.error('Ошибка привязки карты:', errorMessage);
      nfcError = errorMessage;
    }
  }
  
  function handleOpenTopUpModal() {
    if (!selectedGuest) { alert("Please select a guest first."); return; }
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    const topUpData = event.detail;
    topUpError = '';
    try {
      await guestStore.topUpBalance(selectedGuestId, topUpData);
      isTopUpModalOpen = false;
    } catch (error) {
      topUpError = error.message || error.toString();
    }
  }

</script>

<div class="guests-page-layout">
  <div class="list-panel">
    <div class="panel-header">
      <h2>Guests</h2>
      <button on:click={handleOpenCreateModal}>+ New Guest</button>
    </div>
    <GuestSearch bind:searchTerm />
    <div class="button-group">
      <button on:click={guestStore.fetchGuests} disabled={$guestStore.loading}>
        {#if $guestStore.loading}Refreshing...{:else}Refresh List{/if}
      </button>
    </div>
    
    <!-- +++ ИЗМЕНЕНИЕ: Улучшаем отображение состояния загрузки и пустого списка +++ -->
    {#if $guestStore.loading && $guestStore.guests.length === 0}
      <p>Loading guests...</p>
    {:else if $guestStore.error}
      <p class="error">Error: {$guestStore.error}</p>
    {:else if filteredGuests.length === 0}
      <!-- КОММЕНТАРИЙ: Это сообщение теперь будет показываться и когда список пуст,
           и когда поиск ничего не нашел, что является корректным UX. -->
      <p>No guests match your search.</p>
    {:else}
      <GuestList guests={filteredGuests} on:select={handleSelectGuest} selectedId={selectedGuestId} />
    {/if}
  </div>

  {#if selectedGuest}
    <div class="detail-panel">
      <GuestDetail 
        guest={selectedGuest} 
        on:close={handleCloseDetail}
        on:edit={handleOpenEditModal}
        on:bind-card={handleBindCard}
        on:top-up={handleOpenTopUpModal}
      />
    </div>
  {/if}
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

<style>
  /* Стили остаются без изменений */
  .guests-page-layout { display: flex; gap: 1rem; height: calc(100vh - 4rem); }
  .list-panel { flex: 1; overflow-y: auto; display: flex; flex-direction: column; }
  .detail-panel { flex: 1; border-left: 1px solid #ddd; padding-left: 1rem; overflow-y: auto; }
  .error { color: red; }
  .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
  .panel-header h2 { margin: 0; }
  .button-group { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
</style>