<script>
  export let initialSection = 'taps';

  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import BeverageManager from '../components/beverages/BeverageManager.svelte';
  import Modal from '../components/common/Modal.svelte';
  import KegList from '../components/kegs/KegList.svelte';
  import KegForm from '../components/kegs/KegForm.svelte';
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';
  import TapDisplaySettingsModal from '../components/taps/TapDisplaySettingsModal.svelte';
  import TapDrawer from '../components/taps/TapDrawer.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import { beverageStore } from '../stores/beverageStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';

  const sections = {
    taps: {
      title: 'Краны',
      description: 'Оперативная работа по каждому крану: статус, активный налив, подключённая кега и связанные события.',
      permission: 'taps_view',
    },
    inventory: {
      title: 'Кеги и напитки',
      description: 'Инвентарь, каталог напитков и подготовка контента до подключения кранов.',
      permission: 'settings_manage',
    },
    tapScreens: {
      title: 'Экраны кранов',
      description: 'Управление экранами кранов и сценариями показа для гостевых дисплеев.',
      permission: 'display_override',
    },
  };

  let initialLoadAttempted = false;
  let activeTab = initialSection;

  let isKegFormModalOpen = false;
  let kegToEdit = null;
  let kegFormError = '';

  let isAssignModalOpen = false;
  let tapToAssign = null;
  let isAssigning = false;

  let selectedTap = null;
  let isTapDrawerOpen = false;

  let isTapDisplayModalOpen = false;
  let tapForDisplaySettings = null;

  $: activeView = sections[activeTab] || sections.taps;
  $: if ($sessionStore.token && !initialLoadAttempted) {
    tapStore.fetchTaps();
    kegStore.fetchKegs();
    beverageStore.fetchBeverages();
    visitStore.fetchActiveVisits().catch(() => {});
    initialLoadAttempted = true;
  }

  $: tapStore.setOperationalContext({
    activeVisits: $visitStore.activeVisits,
    feedItems: $pourStore.feedItems,
  });

$: if (selectedTap) {
    selectedTap = $tapStore.taps.find((item) => item.tap_id === selectedTap.tap_id) || selectedTap;
  }

  onMount(() => {
    const token = get(sessionStore).token;
    if (token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      beverageStore.fetchBeverages();
      visitStore.fetchActiveVisits().catch(() => {});
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

  function selectTap(tap) {
    selectedTap = tap;
    isTapDrawerOpen = true;
  }


  function requirePermission(permissionKey, message) {
    if ($roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  function handleOpenAssignModal(event) {
    if (!requirePermission('taps_control', 'Назначение кеги доступно только ролям с управлением кранами.')) return;
    tapToAssign = event.detail.tap;
    isAssignModalOpen = true;
  }

  function handleOpenTapDisplaySettings(event) {
    if (!requirePermission('display_override', 'Настройки экрана доступны только management / engineering ролям.')) return;
    tapForDisplaySettings = event.detail.tap;
    isTapDisplayModalOpen = true;
  }

  function handleCloseTapDisplaySettings() {
    isTapDisplayModalOpen = false;
    tapForDisplaySettings = null;
  }

  async function handleTapStatusChange(tap, nextStatus, title) {
    const permissionKey = nextStatus === 'cleaning' || nextStatus === 'locked' ? 'maintenance_actions' : 'taps_control';
    const deniedMessage = permissionKey === 'maintenance_actions'
      ? 'Сервисные действия по крану доступны только старшему смены или инженеру.'
      : 'Управление линией доступно только ролям с правом taps_control.';

    if (!requirePermission(permissionKey, deniedMessage)) return;
    const approved = await uiStore.confirm({
      title,
      message: `Изменить статус ${tap.display_name} на "${nextStatus}"?`,
      confirmText: 'Подтвердить',
      cancelText: 'Отмена',
      danger: nextStatus === 'locked',
    });

    if (!approved) return;

    try {
      await tapStore.updateTapStatus(tap.tap_id, nextStatus);
    } catch (error) {
      uiStore.notifyError(`Ошибка: ${error}`);
    }
  }

  async function handleUnassignTap(tap) {
    if (!tap.keg) return;
    if (!requirePermission('taps_control', 'Снятие кеги доступно только ролям с управлением кранами.')) return;

    const approved = await uiStore.confirm({
      title: 'Снять кегу',
      message: `Отключить кегу "${tap.keg.beverage?.name || 'без названия'}" с ${tap.display_name}?`,
      confirmText: 'Да, снять',
      cancelText: 'Отмена',
      danger: true,
    });

    if (!approved) return;

    try {
      await tapStore.unassignKegFromTap(tap.tap_id);
      kegStore.markKegAsAvailable(tap.keg.keg_id);
    } catch (error) {
      uiStore.notifyError(`Ошибка: ${error}`);
    }
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
    }
  }
</script>

{#if !$roleStore.permissions[activeView.permission]}
  <section class="ui-card restricted">
    <h1>{activeView.title}</h1>
    <p>Текущая роль не предусматривает доступ к этому разделу.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>{activeView.title}</h1>
      <p>{activeView.description}</p>
    </div>
    <nav class="section-tabs" aria-label="Разделы кранов и инвентаря">
      <a href="#/taps" class:active={activeTab === 'taps'}>Краны</a>
      {#if $roleStore.permissions.settings_manage}
        <a href="#/kegs-beverages" class:active={activeTab === 'inventory'}>Кеги и напитки</a>
      {/if}
      {#if $roleStore.permissions.display_override}
        <a href="#/tap-screens" class:active={activeTab === 'tapScreens'}>Экраны кранов</a>
      {/if}
    </nav>
  </div>

  {#if activeTab === 'taps'}
    <section class="operator-layout">
      <div class="section-header">
        <div>
          <h2>Рабочая зона по кранам</h2>
          <p class="section-hint">Каждая карточка показывает состояние крана, напитка, подсистем и текущей сессии. Настройки экрана доступны в карточке конкретного крана.</p>
        </div>
      </div>

      {#if $tapStore.loading && $tapStore.taps.length === 0}
        <p>Загрузка кранов...</p>
      {:else if $tapStore.error}
        <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
      {:else}
        <TapGrid
          taps={$tapStore.taps}
          canControl={$roleStore.permissions.taps_control}
          canMaintain={$roleStore.permissions.maintenance_actions}
          canDisplayOverride={$roleStore.permissions.display_override}
          on:open-detail={(event) => selectTap(event.detail.tap)}
          on:assign={handleOpenAssignModal}
          on:display-settings={handleOpenTapDisplaySettings}
          on:toggle-lock={(event) => handleTapStatusChange(event.detail.tap, event.detail.tap.status === 'active' ? 'locked' : 'active', 'Изменение статуса крана')}
          on:cleaning={(event) => handleTapStatusChange(event.detail.tap, 'cleaning', 'Перевод крана на промывку')}
          on:mark-ready={(event) => handleTapStatusChange(event.detail.tap, 'locked', 'Возврат крана в готовность после работ')}
          on:unassign={(event) => handleUnassignTap(event.detail.tap)}
        />
      {/if}
    </section>
  {:else if activeTab === 'inventory'}
    <div class="inventory-grid">
      <section class="kegs-section">
        <div class="section-header">
          <div>
            <h2>Инвентарь кег</h2>
            <p class="section-hint">Логистика и подготовка запасов вынесены отдельно от операторской панели кранов.</p>
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
            <p class="section-hint">Контент напитков и базовые тексты для гостевого экрана живут отдельно от оперативной работы с tap.</p>
          </div>
        </div>
        <BeverageManager />
      </section>
    </div>
  {:else}
    <section class="ui-card tap-screen-focus">
      <h2>Tap display settings moved into tap detail</h2>
      <p>Чтобы настроить экран конкретного крана, откройте раздел “Краны”, выберите tap и используйте кнопку “Настройки экрана” в detail drawer.</p>
      <a class="back-link" href="#/taps">Перейти к operator screen</a>
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

{#if isTapDrawerOpen && selectedTap}
  <Modal on:close={() => { isTapDrawerOpen = false; selectedTap = null; }}>
    <TapDrawer
      tap={selectedTap}
      canDisplayOverride={$roleStore.permissions.display_override}
      on:close={() => { isTapDrawerOpen = false; selectedTap = null; }}
      on:display-settings={handleOpenTapDisplaySettings}
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
  .section-tabs { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .section-tabs a, .back-link {
    text-decoration: none;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    padding: 0.55rem 0.9rem;
    color: #0f172a;
    font-weight: 600;
    background: #fff;
  }
  .section-tabs a.active { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; }
  .operator-layout, .tap-screen-focus { display: grid; gap: 1rem; }
  .inventory-grid { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); }
  .kegs-section, .beverages-section, .tap-screen-focus { display: grid; gap: 1rem; }
  .hint, .error { margin: 0; }
  .error { color: #b91c1c; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header, .inventory-grid { grid-template-columns: 1fr; display: grid; }
  }
</style>
