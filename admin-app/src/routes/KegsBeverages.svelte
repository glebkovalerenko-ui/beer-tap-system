<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { beverageStore } from '../stores/beverageStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import TapScreens from './TapScreens.svelte';

  const VIEW_MODES = {
    BEVERAGES: 'beverages',
    KEGS: 'kegs',
    SCREENS: 'screens',
  };

  let initialLoadAttempted = false;
  let activeMode = VIEW_MODES.BEVERAGES;
  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';

  $: hasBeverages = $beverageStore.beverages.length > 0;
  $: canViewInventory = $roleStore.permissions.inventory_view
    || $roleStore.permissions.kegs_manage
    || $roleStore.permissions.beverages_catalog_manage
    || $roleStore.permissions.settings_manage;
  $: canManageKegs = $roleStore.permissions.kegs_manage || $roleStore.permissions.settings_manage;
  $: canManageBeveragesCatalog = $roleStore.permissions.beverages_catalog_manage || $roleStore.permissions.settings_manage;
  $: canViewScreens = $roleStore.permissions.display_override || $roleStore.permissions.settings_manage;

  $: if ($sessionStore.token && !initialLoadAttempted) {
    fetchInventoryData();
  }

  onMount(() => {
    if (get(sessionStore).token && !initialLoadAttempted) {
      fetchInventoryData();
    }

    const hash = window.location.hash || '';
    if (hash.startsWith('#/tap-screens') || hash.includes('?tab=screens')) {
      activeMode = VIEW_MODES.SCREENS;
    }
  });

  function fetchInventoryData() {
    kegStore.fetchKegs();
    beverageStore.fetchBeverages();
    initialLoadAttempted = true;
  }

  function switchMode(mode) {
    activeMode = mode;
  }

  function handleOpenCreateModal() {
    if (!canManageKegs) {
      uiStore.notifyWarning('Недостаточно прав для подключения или изменения кеги.');
      return;
    }

    const current = get(beverageStore);
    if (!current?.beverages?.length) {
      uiStore.notifyWarning('Сначала добавьте напиток в каталог, затем создайте кегу.');
      return;
    }

    activeMode = VIEW_MODES.KEGS;
    kegToEdit = null;
    kegFormError = '';
    isKegFormModalOpen = true;
  }

  function closeKegFormModal() {
    isKegFormModalOpen = false;
    kegToEdit = null;
    kegFormError = '';
  }

  async function handleSaveKeg(event) {
    if (!canManageKegs) {
      uiStore.notifyWarning('Недостаточно прав для изменения кеги.');
      return;
    }

    const payload = event.detail;
    const isEditing = Boolean(kegToEdit);
    kegFormError = '';

    try {
      if (isEditing) {
        await kegStore.updateKeg(kegToEdit.keg_id, payload);
      } else {
        await kegStore.createKeg(payload);
      }

      closeKegFormModal();
      activeMode = VIEW_MODES.KEGS;
      uiStore.notifySuccess(isEditing ? 'Кега обновлена.' : 'Кега добавлена.');
    } catch (error) {
      const message = typeof error === 'string' ? error : error instanceof Error ? error.message : 'Неизвестная ошибка';
      kegFormError = `Ошибка при сохранении кеги: ${message}`;
    }
  }

  async function handleDeleteKeg(event) {
    if (!canManageKegs) {
      uiStore.notifyWarning('Недостаточно прав для удаления кеги.');
      return;
    }

    const { keg } = event.detail;
    const isConfirmed = await uiStore.confirm({
      title: 'Удалить кегу?',
      message: `Кега «${keg.beverage.name}» будет удалена без возможности восстановления.`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
      danger: true,
    });

    if (!isConfirmed) {
      return;
    }

    try {
      await kegStore.deleteKeg(keg.keg_id);
      if (kegToEdit?.keg_id === keg.keg_id) {
        closeKegFormModal();
      }
      activeMode = VIEW_MODES.KEGS;
      uiStore.notifySuccess('Кега удалена.');
    } catch (error) {
      const message = typeof error === 'string' ? error : error instanceof Error ? error.message : 'Неизвестная ошибка';
      uiStore.notifyError(`Ошибка при удалении кеги: ${message}`);
    }
  }
</script>

{#if !canViewInventory}
  <section class="ui-card restricted">
    <h1>Кеги и напитки</h1>
    <p>Текущая роль не предусматривает доступ к инвентарю и экранным настройкам.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>{ROUTE_COPY.kegsBeverages.title}</h1>
      <p>{ROUTE_COPY.kegsBeverages.description}</p>
    </div>
  </div>

  <section class="permission-hints">
    <span class:enabled={canViewInventory}>Просмотр</span>
    <span class:enabled={canManageKegs}>Кеги</span>
    <span class:enabled={canManageBeveragesCatalog}>Каталог напитков</span>
    <span class:enabled={canViewScreens}>Screens</span>
  </section>

  <section class="mode-switch-card">
    <div class="mode-switch-copy">
      <h2>Рабочий режим</h2>
      <p>Разделяйте каталог напитков, физические кеги и экраны кранов, чтобы первый слой оставался понятным оператору.</p>
    </div>

    <div class="mode-switch" role="tablist" aria-label="Режим раздела кеги и напитки">
      <button
        type="button"
        role="tab"
        class:active={activeMode === VIEW_MODES.BEVERAGES}
        aria-selected={activeMode === VIEW_MODES.BEVERAGES}
        on:click={() => switchMode(VIEW_MODES.BEVERAGES)}
      >
        Напитки
      </button>
      <button
        type="button"
        role="tab"
        class:active={activeMode === VIEW_MODES.KEGS}
        aria-selected={activeMode === VIEW_MODES.KEGS}
        on:click={() => switchMode(VIEW_MODES.KEGS)}
      >
        Кеги
      </button>
      {#if canViewScreens}
        <button
          type="button"
          role="tab"
          class:active={activeMode === VIEW_MODES.SCREENS}
          aria-selected={activeMode === VIEW_MODES.SCREENS}
          on:click={() => switchMode(VIEW_MODES.SCREENS)}
        >
          Screens
        </button>
      {/if}
    </div>
  </section>

  {#if activeMode === VIEW_MODES.BEVERAGES}
    <section class="mode-panel" aria-labelledby="beverages-mode-title">
      <div class="section-header">
        <div>
          <h2 id="beverages-mode-title">Каталог напитков</h2>
          <p class="section-hint">Каталожный слой: название, стиль, цена, брендинг и контент для гостевого экрана.</p>
        </div>
        <button type="button" class="ghost-link" on:click={() => switchMode(VIEW_MODES.KEGS)}>
          Перейти к кегам
        </button>
      </div>

      <div class="context-note">
        <strong>В этом режиме:</strong>
        редактируйте карточку напитка без смешения с физическими действиями по кеге и крану.
      </div>

      <BeverageManager canManage={canManageBeveragesCatalog} />
    </section>
  {:else if activeMode === VIEW_MODES.KEGS}
    <section class="mode-panel" aria-labelledby="kegs-mode-title">
      <div class="section-header">
        <div>
          <h2 id="kegs-mode-title">Операционный список кег</h2>
          <p class="section-hint">Физическая кега, её остаток, подключение к крану, дата подключения и действия по назначению.</p>
        </div>
        <div class="section-actions">
          <button type="button" class="ghost-link" on:click={() => switchMode(VIEW_MODES.BEVERAGES)}>
            Открыть напиток
          </button>
          <button
            disabled={!canManageKegs || !hasBeverages}
            class:disabled={!canManageKegs || !hasBeverages}
            aria-disabled={!canManageKegs || !hasBeverages}
            title={!canManageKegs ? 'Недостаточно прав для добавления кеги' : !hasBeverages ? 'Сначала добавьте напиток' : 'Добавить кегу'}
            on:click={handleOpenCreateModal}
          >
            + Добавить кегу
          </button>
        </div>
      </div>

      <div class="context-note">
        <strong>В этом режиме:</strong>
        управляйте только физическим запасом и назначением кеги на кран.
      </div>

      {#if !hasBeverages}
        <p class="hint">Каталог напитков пуст. Сначала добавьте напиток, затем создайте кегу.</p>
      {/if}

      {#if $kegStore.loading && $kegStore.kegs.length === 0}
        <p>Загрузка кег...</p>
      {:else if $kegStore.error}
        <p class="error">Ошибка загрузки кег: {$kegStore.error}</p>
      {:else}
        <KegList
          kegs={$kegStore.kegs}
          canManageKegs={canManageKegs}
          on:edit={(event) => {
            if (!canManageKegs) {
              uiStore.notifyWarning('Недостаточно прав для изменения кеги.');
              return;
            }
            kegToEdit = event.detail.keg;
            kegFormError = '';
            activeMode = VIEW_MODES.KEGS;
            isKegFormModalOpen = true;
          }}
          on:delete={handleDeleteKeg}
        />
      {/if}
    </section>
  {:else}
    <section class="mode-panel" aria-labelledby="screens-mode-title">
      <div class="section-header">
        <div>
          <h2 id="screens-mode-title">Экраны кранов</h2>
          <p class="section-hint">Тихий secondary layer для старшего смены и инженерных ролей.</p>
        </div>
        <button type="button" class="ghost-link" on:click={() => switchMode(VIEW_MODES.KEGS)}>
          Вернуться к кегам
        </button>
      </div>

      <div class="context-note">
        <strong>В этом режиме:</strong>
        управляйте guest-facing экраном как вторичным слоем, не смешивая его с базовыми действиями по напитку и кеге.
      </div>

      <TapScreens embedded={true} />
    </section>
  {/if}
{/if}

{#if isKegFormModalOpen}
  <Modal on:close={closeKegFormModal}>
    <KegForm
      keg={kegToEdit}
      isSaving={$kegStore.loading}
      on:save={handleSaveKeg}
      on:cancel={closeKegFormModal}
    />
    {#if kegFormError}
      <p class="error modal-error">{kegFormError}</p>
    {/if}
  </Modal>
{/if}

<style>
  .page-header,
  .section-header,
  .mode-switch-card,
  .section-actions {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .page-header {
    margin-bottom: 1rem;
  }

  .page-header h1,
  .section-header h2,
  .mode-switch-copy h2 {
    margin: 0;
  }

  .page-header p,
  .section-hint,
  .mode-switch-copy p {
    margin: 0.3rem 0 0;
    color: var(--text-secondary, #64748b);
  }

  .permission-hints {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }

  .permission-hints span {
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    font-size: 0.82rem;
    background: #e2e8f0;
    color: #475569;
  }

  .permission-hints span.enabled {
    background: #dcfce7;
    color: #166534;
  }

  .mode-switch-card,
  .mode-panel {
    border: 1px solid var(--border-soft, #e2e8f0);
    border-radius: var(--radius-md, 16px);
    background: var(--bg-surface, #fff);
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .mode-switch-card {
    align-items: center;
  }

  .mode-switch-copy,
  .mode-panel {
    display: grid;
    gap: 1rem;
  }

  .mode-switch {
    display: inline-grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.35rem;
    padding: 0.35rem;
    background: #f1f5f9;
    border-radius: 999px;
  }

  .mode-switch button,
  .ghost-link {
    width: auto;
    margin: 0;
  }

  .mode-switch button {
    min-width: 8rem;
    border-radius: 999px;
    background: transparent;
    color: var(--text-secondary, #475569);
    box-shadow: none;
  }

  .mode-switch button.active {
    background: #1d4ed8;
    color: #fff;
  }

  .context-note {
    padding: 0.85rem 1rem;
    border-radius: 12px;
    background: #f8fafc;
    color: var(--text-primary, #0f172a);
    line-height: 1.45;
  }

  .ghost-link {
    background: #eef2ff;
    color: #23416b;
  }

  .hint,
  .error {
    margin: 0;
  }

  .error {
    color: #b91c1c;
  }

  .restricted {
    padding: 1rem;
  }

  @media (max-width: 980px) {
    .page-header,
    .section-header,
    .mode-switch-card,
    .section-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .mode-switch {
      width: 100%;
    }

    .mode-switch button {
      min-width: 0;
    }
  }
</style>
