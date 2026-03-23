<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import { beverageStore } from '../stores/beverageStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { uiStore } from '../stores/uiStore.js';

  let initialLoadAttempted = false;
  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';

  $: if ($sessionStore.token && !initialLoadAttempted) {
    kegStore.fetchKegs();
    beverageStore.fetchBeverages();
    initialLoadAttempted = true;
  }

  onMount(() => {
    const token = get(sessionStore).token;
    if (token && !initialLoadAttempted) {
      kegStore.fetchKegs();
      beverageStore.fetchBeverages();
      initialLoadAttempted = true;
    }
  });

  function handleOpenCreateModal() {
    const current = get(beverageStore);
    if (!current?.beverages?.length) {
      uiStore.notifyWarning('Сначала добавьте напиток в справочник, затем создайте кегу.');
      return;
    }

    kegToEdit = null;
    kegFormError = '';
    isKegFormModalOpen = true;
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
    }
  }
</script>

{#if !$roleStore.permissions.settings_manage}
  <section class="ui-card restricted">
    <h1>Кеги и напитки</h1>
    <p>Текущая роль не предусматривает доступ к управлению инвентарём.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>Кеги и напитки</h1>
      <p>Инвентарь, каталог напитков и подготовка контента до подключения кранов.</p>
    </div>
  </div>

  <div class="inventory-grid">
    <section class="kegs-section">
      <div class="section-header">
        <div>
          <h2>Инвентарь кег</h2>
          <p class="section-hint">Логистика и подготовка запасов вынесены в самостоятельный экран без внутренних вкладок.</p>
        </div>
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
          <p class="section-hint">Контент напитков и базовые тексты для гостевого экрана живут отдельно от оперативной работы с кранами.</p>
        </div>
      </div>
      <BeverageManager />
    </section>
  </div>
{/if}

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

<style>
  .page-header,
  .section-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }
  .page-header { margin-bottom: 1rem; }
  .page-header h1, .section-header h2 { margin: 0; }
  .page-header p, .section-hint { margin: 0.3rem 0 0; color: var(--text-secondary, #64748b); }
  .inventory-grid { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); }
  .kegs-section, .beverages-section { display: grid; gap: 1rem; }
  .hint, .error { margin: 0; }
  .error { color: #b91c1c; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header, .inventory-grid { grid-template-columns: 1fr; display: grid; }
  }
</style>
