<!-- src/routes/Guests.svelte -->

<script>
  import { onMount } from 'svelte';
  import { guestStore } from '../stores/guestStore.js';

  // --- ИЗМЕНЕНИЕ: Импортируем компоненты для модального окна и формы ---
  import GuestSearch from '../components/guests/GuestSearch.svelte';
  import GuestList from '../components/guests/GuestList.svelte';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';

  // --- Управление состоянием ---
  let searchTerm = '';
  let selectedGuestId = null;

  // --- ИЗМЕНЕНИЕ: Добавляем состояние для модального окна ---
  let isModalOpen = false;
  let formError = '';
  let formKey = 0;

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

  // --- ИЗМЕНЕНИЕ: Новые обработчики для модального окна ---
  function handleOpenCreateModal() {
    formError = ''; // Сбрасываем старые ошибки при открытии
    formKey += 1;
    isModalOpen = true;
  }

  async function handleSave(event) {
    formError = '';
    try {
      // Вызываем метод из стора, передавая ему данные из события 'save'
      await guestStore.createGuest(event.detail);
      isModalOpen = false; // Закрываем окно при успехе
    } catch (error) {
      // Используем тот же надежный паттерн:
      // извлекаем поле `message` из объекта ошибки.
      formError = error.message || error.toString();
    }
  }

</script>

<div class="guests-page-layout">
  <div class="list-panel">
    <!-- ИЗМЕНЕНИЕ: Добавляем обертку для заголовка и кнопки -->
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
      <GuestList guests={filteredGuests} on:select={handleSelectGuest} />
    {/if}
  </div>

  {#if selectedGuest}
    <div class="detail-panel">
      <GuestDetail guest={selectedGuest} on:close={handleCloseDetail} />
    </div>
  {/if}
</div>

<!-- ИЗМЕНЕНИЕ: Добавляем логику модального окна в конец файла -->
{#if isModalOpen}
  <Modal on:close={() => isModalOpen = false}>
    <GuestForm 
      key={formKey}
      on:save={handleSave} 
      on:cancel={() => isModalOpen = false}
      isSaving={$guestStore.loading}
    />
    <!-- Отображение ошибки, если она возникла при сохранении -->
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
    display: flex; /* Добавлено для лучшего контроля дочерних элементов */
    flex-direction: column; /* Добавлено */
  }
  .detail-panel {
    flex: 1;
    border-left: 1px solid #ddd;
    padding-left: 1rem;
    overflow-y: auto;
  }
  .error { color: red; }
  
  /* ИЗМЕНЕНИЕ: Новый стиль для заголовка панели */
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem; /* Добавляем отступ после заголовка */
  }
  .panel-header h2 {
    margin: 0; /* Убираем стандартный отступ у заголовка */
  }
</style>