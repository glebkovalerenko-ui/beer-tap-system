<!-- src/routes/TapsKegs.svelte -->
<script>
  import { sessionStore } from '../stores/sessionStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { beverageStore } from '../stores/beverageStore.js';

  import TapGrid from '../components/taps/TapGrid.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  // +++ НОВЫЙ ИМПОРТ +++
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';

  // --- Локальное состояние для управления UI ---
  let initialLoadAttempted = false;
  
  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';

  // +++ НОВЫЕ ПЕРЕМЕННЫЕ СОСТОЯНИЯ +++
  let isAssignModalOpen = false;
  let tapToAssign = null;
  let isAssigning = false; // Локальный флаг загрузки для модального окна

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      console.log("Токен доступен, загружаем все данные для модуля Taps & Kegs...");
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      beverageStore.fetchBeverages();
      initialLoadAttempted = true;
    }
  }

  // --- Обработчики для CRUD кег (без изменений) ---
  function handleOpenCreateModal() {
    if ($beverageStore.beverages.length === 0) {
      alert("Please add a beverage to the directory before creating a keg.");
      return;
    }
    kegToEdit = null;
    kegFormError = '';
    isKegFormModalOpen = true;
  }
  // ... (остальные обработчики CRUD без изменений)

  // +++ НОВЫЕ ОБРАБОТЧИКИ ДЛЯ НАЗНАЧЕНИЯ КЕГИ +++
  function handleOpenAssignModal(event) {
    tapToAssign = event.detail.tap;
    isAssignModalOpen = true;
  }

  async function handleSaveAssign(event) {
    const { kegId } = event.detail;
    if (!kegId) {
      alert("Please select a keg.");
      return;
    }
    
    isAssigning = true;
    try {
      await tapStore.assignKegToTap(tapToAssign.tap_id, kegId);
      // После успешного назначения, обновим и статус кеги в kegStore
      kegStore.markKegAsUsed(kegId);

      isAssignModalOpen = false;
      tapToAssign = null;
    } catch (error) {
      const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
      alert(`Error assigning keg: ${errorMessage}`);
    } finally {
      isAssigning = false;
    }
  }

</script>

<div class="page-header">
  <h1>Taps & Kegs Management</h1>
</div>

<div class="page-layout">
  
  <section class="taps-section">
    <h2>Taps Status</h2>
    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Loading taps...</p>
    {:else if $tapStore.error}
      <p class="error">Error loading taps: {$tapStore.error}</p>
    {:else}
      <!-- --- ИЗМЕНЕНИЕ: Добавляем обработчик события 'assign' --- -->
      <TapGrid taps={$tapStore.taps} on:assign={handleOpenAssignModal} />
    {/if}
  </section>

  <div class="inventory-grid">
    <section class="kegs-section">
      <div class="section-header">
        <h2>Keg Inventory</h2>
        <button on:click={handleOpenCreateModal}>+ Add New Keg</button>
      </div>
      {#if $kegStore.loading && $kegStore.kegs.length === 0}
        <p>Loading kegs...</p>
      {:else if $kegStore.error}
        <p class="error">Error loading kegs: {$kegStore.error}</p>
      {:else}
        <KegList 
          kegs={$kegStore.kegs}
          on:edit={(e) => { kegToEdit = e.detail.keg; isKegFormModalOpen = true; }}
          on:delete={(e) => { /* логика удаления */ }}
        />
      {/if}
    </section>

    <section class="beverages-section">
       <div class="section-header">
        <h2>Beverage Directory</h2>
      </div>
      <BeverageManager />
    </section>
  </div>
</div>

<!-- Модальное окно для создания/редактирования кеги (без изменений) -->
{#if isKegFormModalOpen}
  <Modal on:close={() => { isKegFormModalOpen = false; kegToEdit = null; }}>
    <KegForm
      keg={kegToEdit}
      isSaving={$kegStore.loading}
      on:save={(e) => { /* логика сохранения */ }}
      on:cancel={() => { isKegFormModalOpen = false; kegToEdit = null; }}
    />
    {#if kegFormError}<p class="error" style="margin-top: 1rem;">{kegFormError}</p>{/if}
  </Modal>
{/if}

<!-- +++ НОВОЕ МОДАЛЬНОЕ ОКНО ДЛЯ НАЗНАЧЕНИЯ КЕГИ +++ -->
{#if isAssignModalOpen}
  <Modal on:close={() => { isAssignModalOpen = false; tapToAssign = null; }}>
    <AssignKegModal
      tap={tapToAssign}
      isSaving={isAssigning}
      on:save={handleSaveAssign}
      on:cancel={() => { isAssignModalOpen = false; tapToAssign = null; }}
    />
  </Modal>
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
  }
  .page-header h1 {
    margin: 0;
  }
  .page-layout {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }
  .error {
    color: red;
  }
  /* --- НОВЫЕ СТИЛИ --- */
  .inventory-grid {
    display: grid;
    grid-template-columns: 2fr 1fr; /* Список кег занимает 2/3, напитки 1/3 */
    gap: 2rem;
    /* Убедимся, что секции могут растягиваться по высоте */
    align-items: start; 
  }
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  .section-header h2 {
    margin: 0;
  }
  .beverages-section {
    /* Эта секция будет растягиваться по высоте вместе с kegs-section */
    display: flex;
    flex-direction: column;
    height: 100%;
  }
</style>