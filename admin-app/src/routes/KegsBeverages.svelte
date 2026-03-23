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

  const VIEW_MODES = {
    BEVERAGES: 'beverages',
    KEGS: 'kegs',
  };

  let initialLoadAttempted = false;
  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';
  let activeMode = VIEW_MODES.BEVERAGES;

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

  $: hasBeverages = $beverageStore.beverages.length > 0;
  $: hasKegs = $kegStore.kegs.length > 0;

  function switchMode(mode) {
    activeMode = mode;
  }

  function handleOpenCreateModal() {
    const current = get(beverageStore);
    if (!current?.beverages?.length) {
      uiStore.notifyWarning('Сначала добавьте напиток в справочник, затем создайте кегу.');
      return;
    }

    kegToEdit = null;
    kegFormError = '';
    activeMode = VIEW_MODES.KEGS;
    isKegFormModalOpen = true;
  }

  async function handleSaveKeg(event) {
    const payload = event.detail;
    kegFormError = '';
    try {
      await kegStore.createKeg(payload);
      isKegFormModalOpen = false;
      kegToEdit = null;
      activeMode = VIEW_MODES.KEGS;
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
      <p>Разделённые рабочие режимы для каталога напитков и операционного списка кег без одновременного показа двух больших форм.</p>
    </div>
  </div>

  <section class="mode-switch-card">
    <div class="mode-switch-copy">
      <h2>Рабочий режим</h2>
      <p>
        Переключайтесь между каталогом напитков и физическим инвентарём кег, чтобы не смешивать контентную настройку и операционные действия.
      </p>
    </div>

    <div class="mode-switch" role="tablist" aria-label="Режим экрана кег и напитков">
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
    </div>
  </section>

  {#if activeMode === VIEW_MODES.BEVERAGES}
    <section class="mode-panel beverages-section" aria-labelledby="beverages-mode-title">
      <div class="section-header">
        <div>
          <h2 id="beverages-mode-title">Каталог напитков</h2>
          <p class="section-hint">Показываем только beverage content/commercial workflow: карточку напитка, guest-facing тексты, цену и display-related поля.</p>
        </div>
        <button type="button" class="ghost-link" on:click={() => switchMode(VIEW_MODES.KEGS)}>
          {hasKegs ? 'Показать подключённые кеги' : 'Перейти к списку кег'}
        </button>
      </div>

      <div class="context-note">
        <strong>В этом режиме:</strong>
        редактируйте каталог, брендовые подписи, описание, цену и визуальные параметры Tap Display без отвлекающих операционных форм по кегам.
      </div>

      <BeverageManager />
    </section>
  {:else}
    <section class="mode-panel kegs-section" aria-labelledby="kegs-mode-title">
      <div class="section-header">
        <div>
          <h2 id="kegs-mode-title">Операционный список кег</h2>
          <p class="section-hint">Показываем только физические сущности: статус, остаток, подключение к крану, дату подключения, учётный ID и действия по назначению.</p>
        </div>
        <div class="section-actions">
          <button type="button" class="ghost-link" on:click={() => switchMode(VIEW_MODES.BEVERAGES)}>
            Открыть связанный напиток
          </button>
          <button
            class:disabled={!hasBeverages}
            aria-disabled={!hasBeverages}
            title={!hasBeverages ? 'Сначала добавьте напиток' : 'Добавить кегу'}
            on:click={handleOpenCreateModal}
          >
            + Добавить кегу
          </button>
        </div>
      </div>

      <div class="context-note">
        <strong>В этом режиме:</strong>
        управляйте запасом и назначением кег без одновременного редактирования guest-facing полей напитка.
      </div>

      {#if !hasBeverages}
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
            activeMode = VIEW_MODES.KEGS;
            isKegFormModalOpen = true;
          }}
          on:delete={() => {}}
        />
      {/if}
    </section>
  {/if}
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

  .mode-switch-copy {
    display: grid;
    gap: 0.15rem;
  }

  .mode-switch {
    display: inline-grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
    min-width: 9rem;
    border-radius: 999px;
    background: transparent;
    color: var(--text-secondary, #475569);
    box-shadow: none;
  }

  .mode-switch button.active {
    background: #1d4ed8;
    color: #fff;
  }

  .mode-panel,
  .kegs-section,
  .beverages-section {
    display: grid;
    gap: 1rem;
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
