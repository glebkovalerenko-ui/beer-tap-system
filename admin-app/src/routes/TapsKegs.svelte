<!-- src/routes/TapsKegs.svelte -->
<script>
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import TapDisplaySettingsModal from '../components/taps/TapDisplaySettingsModal.svelte';
  import { beverageStore } from '../stores/beverageStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';

  let initialLoadAttempted = false;

  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';

  let isAssignModalOpen = false;
  let tapToAssign = null;
  let isAssigning = false;

  let isTapDisplayModalOpen = false;
  let tapForDisplaySettings = null;

  $: if ($sessionStore.token && !initialLoadAttempted) {
    tapStore.fetchTaps();
    kegStore.fetchKegs();
    beverageStore.fetchBeverages();
    initialLoadAttempted = true;
  }

  onMount(() => {
    try {
      const token = get(sessionStore).token;
      if (token && !initialLoadAttempted) {
        tapStore.fetchTaps();
        kegStore.fetchKegs();
        beverageStore.fetchBeverages();
        initialLoadAttempted = true;
      }
    } catch (error) {
      console.error('Ошибка при загрузке TapsKegs:', error);
    }
  });

  function handleOpenCreateModal() {
    try {
      const current = get(beverageStore);
      if (!current || !Array.isArray(current.beverages) || current.beverages.length === 0) {
        uiStore.notifyWarning('Сначала добавьте напиток в справочник, затем создайте кегу.');
        return;
      }

      kegToEdit = null;
      kegFormError = '';
      isKegFormModalOpen = true;
    } catch (error) {
      console.error('Ошибка в handleOpenCreateModal:', error);
      uiStore.notifyError('Не удалось открыть форму кеги. Проверьте состояние API и справочника напитков.');
    }
  }

  function handleOpenAssignModal(event) {
    tapToAssign = event.detail.tap;
    isAssignModalOpen = true;
  }

  function handleOpenTapDisplaySettings(event) {
    tapForDisplaySettings = event.detail.tap;
    isTapDisplayModalOpen = true;
  }

  function handleCloseTapDisplaySettings() {
    isTapDisplayModalOpen = false;
    tapForDisplaySettings = null;
  }

  async function handleSaveAssign(event) {
    const { kegId } = event.detail;
    if (!kegId) {
      uiStore.notifyWarning('Выберите кегу перед назначением.');
      return;
    }

    isAssigning = true;
    try {
      await tapStore.assignKegToTap(tapToAssign.tap_id, kegId);
      kegStore.markKegAsUsed(kegId);
      isAssignModalOpen = false;
      tapToAssign = null;
    } catch (error) {
      const errorMessage = typeof error === 'string' ? error : error instanceof Error ? error.message : 'Неизвестная ошибка';
      uiStore.notifyError(`Ошибка назначения кеги: ${errorMessage}`);
    } finally {
      isAssigning = false;
    }
  }

  async function handleSaveKeg(event) {
    const payload = event.detail;
    kegFormError = '';
    try {
      await kegStore.createKeg(payload);
      isKegFormModalOpen = false;
      kegToEdit = null;
      uiStore.notifySuccess('Кега успешно добавлена.');
    } catch (error) {
      const message = typeof error === 'string' ? error : error instanceof Error ? error.message : 'Неизвестная ошибка';
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
    <div class="section-header">
      <div>
        <h2>Статус кранов</h2>
        <p class="section-hint">Из карточки крана можно открыть назначение кеги и настройки Tap Display.</p>
      </div>
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Загрузка кранов...</p>
    {:else if $tapStore.error}
      <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
    {:else}
      <TapGrid taps={$tapStore.taps} on:assign={handleOpenAssignModal} on:display-settings={handleOpenTapDisplaySettings} />
    {/if}
  </section>

  <div class="inventory-grid">
    <section class="kegs-section">
      <div class="section-header">
        <h2>Инвентарь кег</h2>
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
        <p class="hint">Справочник напитков пуст. Сначала добавьте напиток, затем создайте кегу.</p>
      {/if}

      {#if $kegStore.loading && $kegStore.kegs.length === 0}
        <p>Загрузка кег...</p>
      {:else if $kegStore.error}
        <p class="error">Ошибка загрузки кег: {$kegStore.error}</p>
      {:else}
        <KegList
          kegs={$kegStore.kegs}
          on:edit={(event) => {
            kegToEdit = event.detail.keg;
            isKegFormModalOpen = true;
          }}
          on:delete={() => {}}
        />
      {/if}
    </section>

    <section class="beverages-section">
      <div class="section-header">
        <div>
          <h2>Справочник напитков</h2>
          <p class="section-hint">Здесь оператор настраивает reusable guest-facing контент для Tap Display.</p>
        </div>
      </div>
      <BeverageManager />
    </section>
  </div>
</div>

{#if isKegFormModalOpen}
  <Modal on:close={() => { isKegFormModalOpen = false; kegToEdit = null; }}>
    <KegForm
      keg={kegToEdit}
      isSaving={$kegStore.loading}
      on:save={handleSaveKeg}
      on:cancel={() => { isKegFormModalOpen = false; kegToEdit = null; }}
    />
    {#if kegFormError}
      <p class="error modal-error">{kegFormError}</p>
    {/if}
  </Modal>
{/if}

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

{#if isTapDisplayModalOpen && tapForDisplaySettings}
  <Modal on:close={handleCloseTapDisplaySettings}>
    <TapDisplaySettingsModal
      tap={tapForDisplaySettings}
      on:cancel={handleCloseTapDisplaySettings}
      on:saved={handleCloseTapDisplaySettings}
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

  .inventory-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(340px, 1fr);
    gap: 2rem;
    align-items: start;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .section-header h2 {
    margin: 0;
  }

  .section-header button.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .section-hint,
  .hint {
    margin: 0.35rem 0 0;
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  .beverages-section {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .error {
    color: #c61f35;
  }

  .modal-error {
    margin-top: 1rem;
  }

  @media (max-width: 1180px) {
    .inventory-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 860px) {
    .section-header {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
