<!-- src/routes/Guests.svelte -->

<script>
  import { onMount } from 'svelte';
  import { guestStore } from '../stores/guestStore.js';

  import GuestSearch from '../components/guests/GuestSearch.svelte';
  import GuestList from '../components/guests/GuestList.svelte';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';

  // --- Управление состоянием ---
  let searchTerm = '';
  let selectedGuestId = null;

  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Добавляем состояние для режима редактирования +++
  let isModalOpen = false;
  let formError = '';
  // `guestToEdit` будет хранить данные гостя, когда мы открываем форму для редактирования.
  // Если он `null`, форма работает в режиме создания.
  let guestToEdit = null; 
  // +++ КОНЕЦ ИЗМЕНЕНИЙ +++

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

  // --- Обработчики событий ---
  function handleSelectGuest(event) {
    selectedGuestId = event.detail.guestId;
  }

  function handleCloseDetail() {
    selectedGuestId = null;
  }

  // +++ НАЧАЛО ИЗМЕНЕНИЙ: Обновляем логику работы с модальным окном +++

  // Открывает модальное окно для СОЗДАНИЯ нового гостя
  function handleOpenCreateModal() {
    guestToEdit = null; // Убеждаемся, что мы в режиме создания
    formError = '';
    isModalOpen = true;
  }

  // Открывает модальное окно для РЕДАКТИРОВАНИЯ существующего гостя
  function handleOpenEditModal() {
    guestToEdit = selectedGuest; // Запоминаем, кого редактируем
    formError = '';
    isModalOpen = true;
  }

  // Универсальный обработчик сохранения (для создания и редактирования)
  async function handleSave(event) {
    formError = '';
    try {
      if (guestToEdit) {
        // РЕЖИМ РЕДАКТИРОВАНИЯ
        await guestStore.updateGuest(guestToEdit.guest_id, event.detail);
      } else {
        // РЕЖИМ СОЗДАНИЯ
        await guestStore.createGuest(event.detail);
      }
      isModalOpen = false; // Закрываем окно при успехе
      guestToEdit = null; // Сбрасываем состояние редактирования
    } catch (error) {
      formError = error.message || error.toString();
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
    
    <button on:click={guestStore.fetchGuests} disabled={$guestStore.loading}>
      {#if $guestStore.loading && $guestStore.guests.length === 0}Refreshing...{:else}Refresh List{/if}
    </button>

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
      <!-- +++ ИЗМЕНЕНИЕ: Слушаем новое событие 'edit' +++ -->
      <GuestDetail 
        guest={selectedGuest} 
        on:close={handleCloseDetail}
        on:edit={handleOpenEditModal}
      />
    </div>
  {/if}
</div>

{#if isModalOpen}
  <Modal on:close={() => { isModalOpen = false; guestToEdit = null; }}>
    <!-- +++ ИЗМЕНЕНИЕ: Передаем `guestToEdit` в форму +++ -->
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
</style>