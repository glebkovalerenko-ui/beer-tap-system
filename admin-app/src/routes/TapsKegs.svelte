<!-- src/routes/TapsKegs.svelte -->
<script>
  import { sessionStore } from '../stores/sessionStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { beverageStore } from '../stores/beverageStore.js';
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import TapGrid from '../components/taps/TapGrid.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  // +++ НОВЫЙ ИМПОРТ +++
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';
  import { uiStore } from '../stores/uiStore.js';

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
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      beverageStore.fetchBeverages();
      initialLoadAttempted = true;
    }
  }

  // Дополнительно: при монтировании попробуем загрузить справочник напитков
  // если токен уже доступен — это помогает на старте приложения и в dev-mode
  onMount(() => {
    try {
      const token = get(sessionStore).token;
      if (token && !initialLoadAttempted) {
        // Повторный вызов безопасен, т.к. fetchBeverages проверяет токен
        tapStore.fetchTaps();
        kegStore.fetchKegs();
        beverageStore.fetchBeverages();
        initialLoadAttempted = true;
      }
    } catch (err) {
      console.error('Ошибка при onMount загрузке данных TapsKegs:', err);
    }
  });

  // --- Обработчики для CRUD кег (без изменений) ---
  function handleOpenCreateModal() {
    try {
      // Безопасно читаем текущее состояние справочника напитков
      const current = get(beverageStore);
      if (!current || !Array.isArray(current.beverages) || current.beverages.length === 0) {
        // Явно объясняем пользователю причину недоступности действия
        uiStore.notifyWarning("Сначала добавьте напиток в справочник, прежде чем создавать кегу.");
        return;
      }

      kegToEdit = null;
      kegFormError = '';
      isKegFormModalOpen = true;
    } catch (err) {
      console.error('Ошибка в handleOpenCreateModal:', err);
      // Показываем пользователю простое сообщение об ошибке
      uiStore.notifyError('Не удалось открыть форму создания кеги. Проверьте состояние API и справочника напитков.');
    }
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
      uiStore.notifyWarning("Выберите кегу перед назначением.");
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
      const errorMessage = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Неизвестная ошибка');
      uiStore.notifyError(`Ошибка назначения кеги: ${errorMessage}`);
    } finally {
      isAssigning = false;
    }
  }

  // Обработчик сохранения кеги из формы
  async function handleSaveKeg(event) {
    const payload = event.detail;
    kegFormError = '';
    try {
      await kegStore.createKeg(payload);
      // успешное создание — закрываем модальное окно и показываем подтверждение
      isKegFormModalOpen = false;
      kegToEdit = null;
      uiStore.notifySuccess('Кега успешно добавлена.');
    } catch (error) {
      const message = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Неизвестная ошибка');
      kegFormError = `Ошибка при сохранении кеги: ${message}`;
      console.error('handleSaveKeg error:', error);
    }
  }

</script>

<div class="page-header">
  <h1>Управление кранами и кегами</h1>
</div>

<div class="page-layout">
  
  <section class="taps-section">
    <h2>Статус кранов</h2>
    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Загрузка кранов...</p>
    {:else if $tapStore.error}
      <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
    {:else}
      <!-- --- ИЗМЕНЕНИЕ: Добавляем обработчик события 'assign' --- -->
      <TapGrid taps={$tapStore.taps} on:assign={handleOpenAssignModal} />
    {/if}
  </section>

  <div class="inventory-grid">
    <section class="kegs-section">
      <div class="section-header">
        <h2>Инвентарь кег</h2>
        <!-- Кнопка визуально становится неактивной, но не использует html disabled
             чтобы обработчик клика мог показать поясняющее сообщение. -->
        <button
          class:disabled={$beverageStore.beverages.length === 0}
          aria-disabled={$beverageStore.beverages.length === 0}
          title={$beverageStore.beverages.length === 0 ? 'Сначала добавьте напиток' : 'Добавить кегу'}
          on:click={handleOpenCreateModal}
        >
          + Добавить кегу
        </button>
      </div>
      {#if $beverageStore.beverages.length === 0}
        <p class="hint">Справочник напитков пуст. Добавьте напиток в справочник, прежде чем создавать кегу.</p>
      {/if}
      {#if $kegStore.loading && $kegStore.kegs.length === 0}
        <p>Загрузка кег...</p>
      {:else if $kegStore.error}
        <p class="error">Ошибка загрузки кег: {$kegStore.error}</p>
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
        <h2>Справочник напитков</h2>
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
      on:save={handleSaveKeg}
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
  .section-header button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
    /* сохраняем pointer-events, чтобы обработчик клика мог показать alert */
  }
  .beverages-section {
    /* Эта секция будет растягиваться по высоте вместе с kegs-section */
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  .hint {
    margin: 0.5rem 0 1rem 0;
    color: #666;
    font-size: 0.95rem;
  }
</style>