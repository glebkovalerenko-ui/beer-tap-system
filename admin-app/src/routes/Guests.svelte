<!-- src/routes/Guests.svelte -->

<script>
  import { onMount } from 'svelte';
  import { guestStore } from '../stores/guestStore.js';

  import GuestSearch from '../components/guests/GuestSearch.svelte';
  import GuestList from '../components/guests/GuestList.svelte';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';
  
  import NFCModal from '../components/modals/NFCModal.svelte';

  // --- Управление состоянием ---
  let searchTerm = '';
  let selectedGuestId = null;

  let isModalOpen = false;
  let formError = '';
  let guestToEdit = null; 

  let isNFCModalOpen = false;
  let nfcError = '';

  // --- Загрузка данных (без изменений) ---
  onMount(() => {
    if ($guestStore.guests.length === 0) {
      guestStore.fetchGuests();
    }
  });

  // --- Производные данные (без изменений) ---
  $: filteredGuests = $guestStore.guests.filter(guest => {
    const fullName = `${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`.toLowerCase();
    return fullName.includes(searchTerm.toLowerCase());
  });

  $: selectedGuest = selectedGuestId 
    ? $guestStore.guests.find(g => g.guest_id === selectedGuestId) 
    : null;

  // --- Обработчики событий (без изменений в существующих) ---
  function handleSelectGuest(event) {
    selectedGuestId = event.detail.guestId;
  }

  function handleCloseDetail() {
    selectedGuestId = null;
  }

  function handleOpenCreateModal() {
    guestToEdit = null; 
    formError = '';
    isModalOpen = true;
  }

  function handleOpenEditModal() {
    guestToEdit = selectedGuest;
    formError = '';
    isModalOpen = true;
  }

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

  // --- Обработчики NFC ---
  
  function handleBindCard() {
    if (!selectedGuest) {
      alert("Please select a guest first.");
      return;
    }
    nfcError = ''; 
    isNFCModalOpen = true;
  }

  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Убираем alert и передаем ошибку в дочерний компонент +++
  async function handleUidRead(event) {
    const uid = event.detail.uid;
    console.log(`✅ UID ${uid} получен. Привязываем к гостю ID: ${selectedGuestId}`);
    
    // Сбрасываем ошибку перед новой попыткой
    nfcError = ''; 
    try {
      await guestStore.bindCardToGuest(selectedGuestId, uid);
      // При успехе модальное окно закроется само по таймеру.
    } catch (error) {
      // В случае ошибки от бэкенда...
      const errorMessage = error.message || error.toString();
      console.error('Ошибка привязки карты:', errorMessage);
      
      // ...передаем текст ошибки в дочерний компонент NFCModal.
      nfcError = errorMessage;

      // Убираем alert(), так как теперь ошибку покажет NFCModal.
      // alert(`Failed to bind card: ${nfcError}`);

      // Не закрываем модальное окно, чтобы пользователь увидел ошибку.
    }
  }
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++

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
        {#if $guestStore.loading && $guestStore.guests.length === 0}Refreshing...{:else}Refresh List{/if}
      </button>
    </div>

    {#if $guestStore.loading && $guestStore.guests.length === 0}
      <p>Loading guests...</p>
    {:else if $guestStore.error}
      <p class="error">Error: {$guestStore.error}</p>
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
    {#if formError}
      <p class="error" style="margin-top: 1rem;">{formError}</p>
    {/if}
  </Modal>
{/if}

<!-- +++ НАЧАЛО ИЗМЕНЕНИЙ: Передаем ошибку в NFCModal через prop +++ -->
{#if isNFCModalOpen}
  <NFCModal 
    on:close={() => { isNFCModalOpen = false; }}
    on:uid-read={handleUidRead}
    externalError={nfcError}
  />
{/if}
<!-- +++ КОНЕЦ ИЗМЕНЕНИЙ +++ -->


<style>
  .guests-page-layout {
    display: flex;
    gap: 1rem;
    height: calc(100vh - 4rem);
  }
  .list-panel {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }
  .detail-panel {
    flex: 1;
    border-left: 1px solid #ddd;
    padding-left: 1rem;
    overflow-y: auto;
  }
  .error { color: red; }
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem; 
  }
  .panel-header h2 {
    margin: 0;
  }
  
  .button-group {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
</style>