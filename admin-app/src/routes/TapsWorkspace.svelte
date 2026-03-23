<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import Modal from '../components/common/Modal.svelte';
  import SideDrawer from '../components/common/SideDrawer.svelte';
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';
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

  let initialLoadAttempted = false;
  let isAssignModalOpen = false;
  let tapToAssign = null;
  let isAssigning = false;
  let selectedTap = null;
  let isTapDrawerOpen = false;

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

    const focusTapId = sessionStorage.getItem('incidents.focusTapId');
    if (focusTapId) {
      sessionStorage.removeItem('incidents.focusTapId');
      const openTapWhenReady = () => {
        const target = $tapStore.taps.find((item) => String(item.tap_id) === String(focusTapId));
        if (target) {
          selectTap(target);
          return true;
        }
        return false;
      };

      if (!openTapWhenReady()) {
        const unsubscribe = tapStore.subscribe((state) => {
          if (state.taps?.length && openTapWhenReady()) {
            unsubscribe();
          }
        });
      }
    }
  });

  function selectTap(tap) {
    selectedTap = tap;
    isTapDrawerOpen = true;
  }

  function openSessionFromTap(event) {
    const visitId = event.detail.visitId || event.detail.tap?.operations?.activeSessionSummary?.visitId || null;
    const tapId = event.detail.tap?.tap_id || event.detail.tapId || null;
    if (visitId) {
      sessionStorage.setItem('visits.lookupVisitId', visitId);
    }
    if (tapId) {
      sessionStorage.setItem('sessions.history.tapId', String(tapId));
    }
    window.location.hash = '#/sessions/history';
  }

  function requirePermission(permissionKey, message) {
    if ($roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  function openTapDisplayRoute(tap) {
    if (!requirePermission('display_override', 'Настройки экрана доступны только management / engineering ролям.')) return;
    sessionStorage.setItem('tapScreens.focusTapId', String(tap.tap_id));
    window.location.hash = '#/tap-screens';
  }

  function handleOpenAssignModal(event) {
    if (!requirePermission('taps_control', 'Назначение кеги доступно только ролям с управлением кранами.')) return;
    tapToAssign = event.detail.tap;
    isAssignModalOpen = true;
  }

  function handleOpenTapDisplaySettings(event) {
    openTapDisplayRoute(event.detail.tap);
  }


  async function handleTapStatusChange(tap, nextStatus, title, options = {}) {
    const permissionKey = options.permissionKey || (nextStatus === 'cleaning' ? 'maintenance_actions' : 'taps_control');
    const deniedMessage = options.deniedMessage || (permissionKey === 'maintenance_actions'
      ? 'Сервисные действия по крану доступны только старшему смены или инженеру.'
      : 'Управление линией доступно только ролям с правом taps_control.');

    if (!requirePermission(permissionKey, deniedMessage)) return;
    const approved = await uiStore.confirm({
      title,
      message: options.message || `Изменить статус ${tap.display_name} на "${nextStatus}"?`,
      confirmText: options.confirmText || 'Подтвердить',
      cancelText: 'Отмена',
      danger: options.danger ?? nextStatus === 'locked',
    });

    if (!approved) return;

    try {
      await tapStore.updateTapStatus(tap.tap_id, nextStatus);
    } catch (error) {
      uiStore.notifyError(`Ошибка: ${error}`);
    }
  }

  async function handleStopPour(tap) {
    if (!tap?.operations?.activeSessionSummary) {
      uiStore.notifyWarning('На этом кране нет активной сессии для остановки.');
      return;
    }

    await handleTapStatusChange(tap, 'locked', 'Остановить налив и заблокировать кран', {
      permissionKey: 'taps_control',
      message: `Остановить текущий налив на ${tap.display_name} и перевести кран в блокировку?`,
      confirmText: 'Остановить налив',
      danger: true,
    });
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
</script>

{#if !$roleStore.permissions.taps_view}
  <section class="ui-card restricted">
    <h1>Краны</h1>
    <p>Текущая роль не предусматривает доступ к рабочей зоне кранов.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>Краны</h1>
      <p>Оперативная работа по каждому крану: статус, активный налив, подключённая кега и связанные события.</p>
    </div>
  </div>

  <section class="operator-layout">
    <div class="section-header">
      <div>
        <h2>Рабочая зона по кранам</h2>
        <p class="section-hint">Каждая карточка показывает состояние крана, напитка, подсистем и текущей сессии. Переход к управлению экраном вынесен в отдельный route-level экран.</p>
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
        on:open-history={openSessionFromTap}
        on:stop-pour={(event) => handleStopPour(event.detail.tap)}
        on:toggle-lock={(event) => handleTapStatusChange(event.detail.tap, event.detail.tap.status === 'locked' ? 'active' : 'locked', event.detail.tap.status === 'locked' ? 'Разблокировать кран' : 'Заблокировать кран')}
        on:cleaning={(event) => handleTapStatusChange(event.detail.tap, 'cleaning', 'Перевод крана на промывку')}
        on:mark-ready={(event) => handleTapStatusChange(event.detail.tap, 'active', 'Вернуть кран в готовность', {
          permissionKey: 'maintenance_actions',
          message: `Перевести ${event.detail.tap.display_name} в статус "active" после сервисных работ?`,
          confirmText: 'Вернуть в готовность',
          danger: false,
        })}
        on:unassign={(event) => handleUnassignTap(event.detail.tap)}
      />
    {/if}
  </section>
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
  <SideDrawer
    showHeader={false}
    width="min(760px, 100vw)"
    labelledBy="tap-drawer-title"
    describedBy="tap-drawer-description"
    on:close={() => { isTapDrawerOpen = false; selectedTap = null; }}
  >
    <TapDrawer
      tap={selectedTap}
      canDisplayOverride={$roleStore.permissions.display_override}
      canControl={$roleStore.permissions.taps_control}
      on:close={() => { isTapDrawerOpen = false; selectedTap = null; }}
      on:display-settings={handleOpenTapDisplaySettings}
      on:open-session={openSessionFromTap}
      on:stop-pour={(event) => handleStopPour(event.detail.tap)}
      on:toggle-lock={(event) => handleTapStatusChange(event.detail.tap, event.detail.tap.status === 'locked' ? 'active' : 'locked', event.detail.tap.status === 'locked' ? 'Разблокировать кран' : 'Заблокировать кран')}
    />
  </SideDrawer>
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
  .operator-layout { display: grid; gap: 1rem; position: relative; }
  .error { margin: 0; color: #b91c1c; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header { grid-template-columns: 1fr; display: grid; }
  }
</style>
