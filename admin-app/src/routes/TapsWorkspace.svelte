<script>
  import { onMount } from 'svelte';

  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import Modal from '../components/common/Modal.svelte';
  import SideDrawer from '../components/common/SideDrawer.svelte';
  import AssignKegModal from '../components/modals/AssignKegModal.svelte';
  import TapDrawer from '../components/taps/TapDrawer.svelte';
  import TapGrid from '../components/taps/TapGrid.svelte';
  import { buildOperatorActionRequest } from '../lib/operator/actionDialogModel.js';
  import { operatorActionStore } from '../stores/operatorActionStore.js';
  import { resolveSessionHistoryTargets } from '../lib/tapWorkspaceHelpers.js';
  import { beverageStore } from '../stores/beverageStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';

  let isAssignModalOpen = false;
  /** @type {any} */
  let tapToAssign = null;
  let isAssigning = false;
  /** @type {any} */
  let selectedTap = null;
  let isTapDrawerOpen = false;
  /** @type {any} */
  let permissions = {};
  /** @type {any[]} */
  let taps = [];
  $: permissions = /** @type {any} */ ($roleStore.permissions || {});
  $: taps = /** @type {any[]} */ ($tapStore.taps || []);
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Backend temporarily degraded. Tap mutations stay read-only until fresh data returns.')
    : '';

  /** @typedef {import('../lib/tapWorkspaceHelpers.js').TapWorkspaceOpenHistoryPayload} TapHistoryPayload */
  /** @typedef {CustomEvent<{ tap: any }>} TapDetailEvent */
  /** @typedef {CustomEvent<{ kegId: string|number }>} AssignSaveEvent */

  $: tapStore.setOperationalContext({
    activeVisits: $visitStore.activeVisits,
    feedItems: $pourStore.feedItems,
  });

  $: if (selectedTap) {
    selectedTap = taps.find((item) => item.tap_id === selectedTap.tap_id) || selectedTap;
  }

  onMount(() => {
    if (($kegStore.kegs || []).length === 0 && !$kegStore.loading) {
      kegStore.fetchKegs();
    }
    if (($beverageStore.beverages || []).length === 0 && !$beverageStore.loading) {
      beverageStore.fetchBeverages();
    }

    const focusTapId = sessionStorage.getItem('incidents.focusTapId');
    if (focusTapId) {
      sessionStorage.removeItem('incidents.focusTapId');
      const openTapWhenReady = () => {
        const target = taps.find((item) => String(item.tap_id) === String(focusTapId));
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

  /** @param {any} tap */
  async function selectTap(tap) {
    selectedTap = tap;
    isTapDrawerOpen = true;
    try {
      const tapDetail = await tapStore.fetchTapDetail(tap.tap_id, { updateStore: true });
      if (selectedTap?.tap_id === tap.tap_id) {
        selectedTap = tapDetail;
      }
    } catch {
      // Keep the already opened drawer with the best available card data.
    }
  }

  /** @param {CustomEvent<TapHistoryPayload>} event */
  function openSessionFromTap(event) {
    const { visitId, tapId } = resolveSessionHistoryTargets(event.detail);
    if (visitId) {
      sessionStorage.setItem('visits.lookupVisitId', String(visitId));
    }
    if (tapId) {
      sessionStorage.setItem('sessions.history.tapId', String(tapId));
    }
    window.location.hash = '#/sessions/history';
  }

  /** @param {string} permissionKey @param {string} message */
  function requirePermission(permissionKey, message) {
    if (routeReadOnlyReason) {
      uiStore.notifyWarning(routeReadOnlyReason);
      return false;
    }
    if (permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  /** @param {any} tap */
  function openTapDisplayRoute(tap) {
    if (!requirePermission('display_override', 'Настройки экрана доступны только management / engineering ролям.')) return;
    sessionStorage.setItem('tapScreens.focusTapId', String(tap.tap_id));
    window.location.hash = '#/tap-screens';
  }

  /** @param {TapDetailEvent} event */
  function handleOpenAssignModal(event) {
    if (!requirePermission('taps_control', 'Назначение кеги доступно только ролям с управлением кранами.')) return;
    tapToAssign = event.detail.tap;
    isAssignModalOpen = true;
  }

  /** @param {TapDetailEvent} event */
  function handleOpenTapDisplaySettings(event) {
    openTapDisplayRoute(event.detail.tap);
  }


  /** @param {any} tap @param {string} nextStatus @param {string} title @param {{permissionKey?: string, deniedMessage?: string, message?: string, confirmText?: string, danger?: boolean}} [options] */
  async function handleTapStatusChange(tap, nextStatus, actionKey, options = {}) {
    const permissionKey = options.permissionKey || null;
    const allowedByPermission = permissionKey ? Boolean(permissions[permissionKey]) : true;
    const deniedMessage = options.deniedMessage || (permissionKey === 'maintenance_actions'
      ? 'Сервисные действия по крану доступны только старшему смены или инженеру.'
      : 'Управление линией доступно только ролям с правом taps_control.');

    const policy = options.policy || {
      allowed: allowedByPermission,
      confirm_required: true,
      disabled_reason: allowedByPermission ? null : deniedMessage,
    };
    const resolvedActionKey = String(actionKey || '').startsWith('tap.')
      ? actionKey
      : nextStatus === 'cleaning'
        ? 'tap.cleaning'
        : (nextStatus === 'active' && permissionKey === 'maintenance_actions')
          ? 'tap.mark_ready'
          : nextStatus === 'active'
            ? 'tap.unlock'
            : 'tap.lock';
    const request = buildOperatorActionRequest({
      actionKey: resolvedActionKey,
      policy,
      context: { tap },
      readOnlyReason: routeReadOnlyReason,
      overrides: {
        description: options.message,
        submitText: options.confirmText,
        danger: options.danger,
      },
    });

    if (request.blockedReason) {
      uiStore.notifyWarning(request.blockedReason);
      return;
    }

    const submission = await operatorActionStore.open(request);
    if (!submission) return;

    try {
      await tapStore.updateTapStatus(tap.tap_id, {
        status: nextStatus,
        reasonCode: submission.values.reasonCode || null,
        comment: submission.values.comment || null,
      });
    } catch (error) {
      uiStore.notifyError(`Ошибка: ${error}`);
    }
  }

  /** @param {any} tap */
  async function handleStopPour(tap) {
    if (!tap?.operations?.activeSessionSummary) {
      uiStore.notifyWarning('На этом кране нет активной сессии для остановки.');
      return;
    }

    await handleTapStatusChange(tap, 'locked', 'tap.stop', {
      policy: tap?.safe_actions?.stop,
      message: `Stop the current pour on ${tap.display_name} and move the tap to locked state?`,
      confirmText: 'Stop pour',
      danger: true,
    });
  }

  /** @param {any} tap */
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

  /** @param {AssignSaveEvent} event */
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

{#if !permissions.taps_view}
  <section class="ui-card restricted">
    <h1>Краны</h1>
    <p>Текущая роль не предусматривает доступ к рабочей зоне кранов.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>{ROUTE_COPY.taps.title}</h1>
      <p>{ROUTE_COPY.taps.description}</p>
    </div>
    <DataFreshnessChip
      label="Taps"
      lastFetchedAt={$tapStore.lastFetchedAt}
      staleAfterMs={$tapStore.staleTtlMs}
      mode={$operatorConnectionStore.mode}
      transport={$operatorConnectionStore.transport}
      reason={$operatorConnectionStore.reason}
    />
  </div>

  <section class="operator-layout">
    {#if routeReadOnlyReason}
      <div class="error-banner">{routeReadOnlyReason}</div>
    {/if}
    <div class="section-header">
      <div>
        <h2>Рабочая зона по кранам</h2>
        <p class="section-hint">Каждая карточка показывает состояние крана, напитка, подсистем и текущей сессии. Экран крана, кега и история доступны без потери общего обзора.</p>
      </div>
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Загрузка кранов...</p>
    {:else if $tapStore.error}
      <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
    {:else}
      <TapGrid
        taps={taps}
        canControl={permissions.taps_control}
        canDisplayOverride={permissions.display_override}
        {permissions}
        readOnlyReason={routeReadOnlyReason}
        on:open-detail={(event) => selectTap(event.detail.tap)}
        on:assign={handleOpenAssignModal}
        on:display-settings={handleOpenTapDisplaySettings}
        on:open-history={openSessionFromTap}
        on:stop-pour={(event) => handleStopPour(event.detail.tap)}
        on:toggle-lock={(event) => handleTapStatusChange(
          event.detail.tap,
          event.detail.tap.status === 'locked' ? 'active' : 'locked',
          event.detail.tap.status === 'locked' ? 'tap.unlock' : 'tap.lock'
        )}
        on:cleaning={(event) => handleTapStatusChange(event.detail.tap, 'cleaning', 'tap.cleaning')}
        on:mark-ready={(event) => handleTapStatusChange(event.detail.tap, 'active', 'tap.mark_ready', {
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
        {permissions}
        readOnlyReason={routeReadOnlyReason}
        on:close={() => { isTapDrawerOpen = false; selectedTap = null; }}
        on:display-settings={handleOpenTapDisplaySettings}
      on:open-session={openSessionFromTap}
      on:stop-pour={(event) => handleStopPour(event.detail.tap)}
      on:toggle-lock={(event) => handleTapStatusChange(
        event.detail.tap,
        event.detail.tap.status === 'locked' ? 'active' : 'locked',
        event.detail.tap.status === 'locked' ? 'tap.unlock' : 'tap.lock'
      )}
      on:assign={handleOpenAssignModal}
      on:unassign={(event) => handleUnassignTap(event.detail.tap)}
      on:cleaning={(event) => handleTapStatusChange(event.detail.tap, 'cleaning', 'tap.cleaning')}
      on:mark-ready={(event) => handleTapStatusChange(event.detail.tap, 'active', 'tap.mark_ready', {
        permissionKey: 'maintenance_actions',
        message: `Перевести ${event.detail.tap.display_name} в статус "active" после сервисных работ?`,
        confirmText: 'Вернуть в готовность',
        danger: false,
      })}
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
  .error-banner { margin: 0; padding: 0.9rem 1rem; border: 1px solid #fcd34d; border-radius: 14px; background: #fff7ed; color: #9a3412; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header { grid-template-columns: 1fr; display: grid; }
  }
</style>
