<script>
  import { onMount } from 'svelte';

  export let systemMode = false;
  import { tapStore } from '../stores/tapStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import { kegStore } from '../stores/kegStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { nfcReaderStore } from '../stores/nfcReaderStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { normalizeErrorMessage } from '../lib/errorUtils';
  import { serverConfigStore, SHOW_API_BASE_URL } from '../lib/config.js';

  import TapGrid from '../components/taps/TapGrid.svelte';
  import PourFeed from '../components/pours/PourFeed.svelte';
  import FlowSummaryPanel from '../components/pours/FlowSummaryPanel.svelte';
  import InvestorValuePanel from '../components/system/InvestorValuePanel.svelte';
  import Modal from '../components/common/Modal.svelte';
  import ShiftReportView from '../components/reports/ShiftReportView.svelte';
  import { formatDateTimeRu, formatMinorUnitsRub, formatTimeRu, formatVolumeRu } from '../lib/formatters.js';

  let initialLoadAttempted = false;
  let showConfirmModal = false;
  let showReportModal = false;
  let reportTitle = '';
  let reportPayload = null;
  let reportId = null;
  let zReports = [];
  let zReportsLoading = false;
  let zFilterInitialized = false;
  let fromDate = '';
  let toDate = '';
  let now = new Date();
  let dismissedAlertKeys = new Set();

  const todayString = () => {
    const current = new Date();
    const year = current.getFullYear();
    const month = String(current.getMonth() + 1).padStart(2, '0');
    const day = String(current.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const LOW_KEG_THRESHOLD = 0.15;
  const HEARTBEAT_STALE_MINUTES = 5;

  function toNumber(value) {
    const parsed = Number.parseFloat(String(value ?? '0').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function isToday(isoValue) {
    if (!isoValue) return false;
    const date = new Date(isoValue);
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  }

  function formatShiftState() {
    if ($shiftStore.isOpen) {
      return $shiftStore.shift?.opened_at ? `Открыта с ${formatDateTimeRu($shiftStore.shift.opened_at)}` : 'Смена открыта';
    }
    if ($shiftStore.shift?.closed_at) {
      return `Закрыта ${formatDateTimeRu($shiftStore.shift.closed_at)}`;
    }
    return 'Смена закрыта';
  }

  function healthTone(state) {
    return state === 'ok' ? 'ok' : state === 'warning' ? 'warning' : 'critical';
  }

  function navigateTo(path) {
    window.location.hash = path;
  }

  function requirePermission(permissionKey, message) {
    if ($roleStore.permissions[permissionKey]) {
      return true;
    }
    uiStore.notifyWarning(message);
    return false;
  }

  function dismissAlert(key) {
    dismissedAlertKeys = new Set([...dismissedAlertKeys, key]);
  }

  function acknowledgeAlert(item) {
    dismissAlert(item.key);
    uiStore.notifySuccess(`Отмечено: ${item.title}`);
  }

  function openAlertTarget(item) {
    navigateTo(item.href);
  }

  function statusLabel(status) {
    const labels = {
      ok: 'в норме',
      warning: 'требует внимания',
      critical: 'критично',
    };
    return labels[status] || status;
  }

  function minutesSince(isoValue) {
    if (!isoValue) return Number.POSITIVE_INFINITY;
    const timestamp = new Date(isoValue).getTime();
    if (Number.isNaN(timestamp)) return Number.POSITIVE_INFINITY;
    return Math.floor((now.getTime() - timestamp) / 60000);
  }

  $: currentShiftId = $shiftStore.shift?.id || null;
  $: canCreateOrShowCurrentZ = !$shiftStore.isOpen && $shiftStore.shift?.status === 'closed' && !!currentShiftId;

  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      kegStore.fetchKegs();
      shiftStore.fetchCurrent();
      visitStore.fetchActiveVisits();
      initialLoadAttempted = true;
    }
  }

  $: {
    if ($sessionStore.token && !zFilterInitialized) {
      const today = todayString();
      fromDate = today;
      toDate = today;
      zFilterInitialized = true;
      loadZReports();
    }
  }

  onMount(() => {
    const timer = setInterval(() => {
      now = new Date();
    }, 1000);

    return () => clearInterval(timer);
  });

  async function openReportModal({ title, payload, id = null }) {
    reportTitle = title;
    reportPayload = payload;
    reportId = id;
    showReportModal = true;
  }

  async function handleEmergencyStopToggle() {
    if (!requirePermission('maintenance_actions', 'Экстренная остановка доступна только сервисному уровню.')) return;
    const newState = !$systemStore.emergencyStop;
    try {
      await systemStore.setEmergencyStop(newState);
      showConfirmModal = false;
    } catch (error) {
      uiStore.notifyError(`Ошибка изменения состояния: ${normalizeErrorMessage(error)}`);
    }
  }

  async function openShift() {
    try {
      await shiftStore.openShift();
      uiStore.notifySuccess('Смена открыта.');
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function closeShift() {
    try {
      await shiftStore.closeShift();
      uiStore.notifySuccess('Смена закрыта.');
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function showXReport() {
    if (!$shiftStore.isOpen || !currentShiftId) {
      uiStore.notifyWarning('X-отчёт доступен только для активной смены.');
      return;
    }
    try {
      const payload = await shiftStore.fetchXReport(currentShiftId);
      openReportModal({ title: 'X-отчёт смены', payload });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function createZReport() {
    if (!canCreateOrShowCurrentZ) {
      uiStore.notifyWarning('Сначала закройте смену, затем сформируйте Z-отчёт.');
      return;
    }
    try {
      const report = await shiftStore.createZReport(currentShiftId);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
      await loadZReports();
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function showCurrentZReport() {
    if (!canCreateOrShowCurrentZ) {
      uiStore.notifyWarning('Нет закрытой смены для показа Z-отчёта.');
      return;
    }
    try {
      const report = await shiftStore.fetchZReport(currentShiftId);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  async function loadZReports() {
    if (!fromDate || !toDate) {
      uiStore.notifyWarning('Заполните даты фильтра для поиска Z-отчётов.');
      return;
    }
    zReportsLoading = true;
    try {
      zReports = await shiftStore.listZReports(fromDate, toDate);
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    } finally {
      zReportsLoading = false;
    }
  }

  async function openReportFromList(item) {
    try {
      const report = await shiftStore.fetchZReport(item.shift_id);
      openReportModal({
        title: 'Z-отчёт смены',
        payload: report.payload,
        id: report.report_id,
      });
    } catch (error) {
      uiStore.notifyError(normalizeErrorMessage(error));
    }
  }

  $: poursToday = $pourStore.pours.filter((item) => isToday(item.poured_at));
  $: liveFlowItems = $pourStore.feedItems.filter((item) => item.item_type === 'flow_event' && item.event_status !== 'stopped');
  $: activeTaps = $tapStore.taps.filter((tap) => tap.status === 'active');
  $: tapsWithoutKeg = $tapStore.taps.filter((tap) => !tap.keg_id);
  $: lowKegs = $kegStore.kegs.filter((keg) => {
    const initial = toNumber(keg.initial_volume_ml);
    const current = toNumber(keg.current_volume_ml);
    return initial > 0 && (current / initial) <= LOW_KEG_THRESHOLD;
  });
  $: revenueToday = poursToday.reduce((sum, item) => sum + toNumber(item.amount_charged), 0);
  $: volumeTodayMl = poursToday.reduce((sum, item) => sum + toNumber(item.volume_ml), 0);
  $: sessionsToday = new Set(
    poursToday
      .map((item) => item.visit_id || item.session_id || item.guest?.guest_id)
      .filter(Boolean)
  ).size;
  $: openIncidents = ($systemStore.emergencyStop ? 1 : 0) + liveFlowItems.filter((item) => item.reason && item.reason !== 'authorized_pour_in_progress').length + tapsWithoutKeg.length;
  $: nonSaleFlowCount = ($pourStore.flowSummary?.non_sale_breakdown || []).reduce((sum, item) => sum + (toNumber(item.volume_ml) > 0 ? 1 : 0), 0);

  $: backendHealth = $tapStore.error || $pourStore.error || $shiftStore.error || $systemStore.error
    ? { key: 'backend', label: 'Backend', state: 'critical', detail: 'Есть ошибки загрузки данных' }
    : { key: 'backend', label: 'Backend', state: 'ok', detail: 'Данные обновляются' };

  $: controllerHealth = $nfcReaderStore.status === 'error'
    ? { key: 'controller', label: 'Controller', state: 'critical', detail: 'Есть ошибки в полевом контуре' }
    : $nfcReaderStore.status === 'disconnected' || $nfcReaderStore.status === 'recovering' || liveFlowItems.length > 0
      ? { key: 'controller', label: 'Controller', state: 'warning', detail: 'Проверьте события и соединение' }
      : { key: 'controller', label: 'Controller', state: 'ok', detail: 'Контроллеры отвечают' };

  $: displayAgentHealth = SHOW_API_BASE_URL && !$serverConfigStore.baseUrl
    ? { key: 'display', label: 'Display-agent', state: 'warning', detail: 'Нет подтверждённого адреса display API' }
    : { key: 'display', label: 'Display-agent', state: 'ok', detail: 'Маршрут до display задан' };

  $: overallHealth = [backendHealth, controllerHealth, displayAgentHealth].some((item) => item.state === 'critical')
    ? 'critical'
    : [backendHealth, controllerHealth, displayAgentHealth].some((item) => item.state === 'warning')
      ? 'warning'
      : 'ok';

  $: staleTapHeartbeatAlerts = $tapStore.taps
    .filter((tap) => minutesSince(tap.last_heartbeat_at || tap.updated_at) >= HEARTBEAT_STALE_MINUTES)
    .map((tap) => ({
      key: `heartbeat-${tap.tap_id}`,
      title: tap.display_name || `Кран #${tap.tap_id}`,
      description: `Нет heartbeat ${minutesSince(tap.last_heartbeat_at || tap.updated_at)} мин`,
      category: 'stale device heartbeat',
      severity: 'warning',
      href: '#/system',
      primaryCta: 'Открыть систему',
      secondaryCta: 'Скрыть',
      meta: 'heartbeat',
    }));

  $: attentionItems = [
    ...tapsWithoutKeg.map((tap) => ({
      key: `tap-no-keg-${tap.tap_id}`,
      title: tap.display_name || `Кран #${tap.tap_id}`,
      description: 'Кран без назначенной кеги и не готов к продаже.',
      category: 'taps without keg',
      severity: 'warning',
      href: '#/taps',
      primaryCta: 'Открыть кран',
      secondaryCta: 'Скрыть',
      meta: tap.status === 'active' ? 'активен без кеги' : 'ожидает назначения',
    })),
    ...($nfcReaderStore.status === 'disconnected' || $nfcReaderStore.status === 'error' || $nfcReaderStore.status === 'recovering'
      ? [{
          key: `reader-${$nfcReaderStore.status}`,
          title: 'NFC reader offline',
          description: $nfcReaderStore.message || $nfcReaderStore.error || 'Считыватель требует проверки.',
          category: 'offline controllers/readers/displays',
          severity: $nfcReaderStore.status === 'error' ? 'critical' : 'warning',
          href: '#/system',
          primaryCta: 'Открыть систему',
          secondaryCta: 'Подтвердить',
          meta: 'reader',
        }]
      : []),
    ...liveFlowItems
      .filter((item) => item.reason === 'authorized_pour_in_progress')
      .map((item) => ({
        key: `stuck-sync-${item.item_id}`,
        title: item.tap_name || `Кран #${item.tap_id}`,
        description: 'Сессия льёт и ждёт синхронизацию с контроллером.',
        category: 'stuck sync',
        severity: 'warning',
        href: '#/sessions',
        primaryCta: 'Открыть сессию',
        secondaryCta: 'Подтвердить',
        meta: formatTimeRu(item.timestamp),
      })),
    ...liveFlowItems
      .filter((item) => item.reason && item.reason !== 'authorized_pour_in_progress')
      .map((item) => ({
        key: `non-sale-${item.item_id}`,
        title: item.tap_name || `Кран #${item.tap_id}`,
        description: 'Зафиксирован пролив вне продажи или при закрытом клапане.',
        category: 'non-sale flow',
        severity: 'critical',
        href: '#/sessions',
        primaryCta: 'Открыть сессию',
        secondaryCta: 'Подтвердить',
        meta: item.reason,
      })),
    ...staleTapHeartbeatAlerts,
  ]
    .filter((item) => !dismissedAlertKeys.has(item.key))
    .sort((left, right) => {
      const weight = { critical: 0, warning: 1, info: 2 };
      return (weight[left.severity] ?? 3) - (weight[right.severity] ?? 3);
    });

  $: todayKpis = [
    {
      label: 'Активные краны',
      value: `${activeTaps.length}`,
      note: `${$tapStore.taps.length || 0} всего · ${tapsWithoutKeg.length} без кеги`,
      tone: activeTaps.length > 0 ? 'neutral' : 'warning',
    },
    {
      label: 'Льют сейчас',
      value: `${liveFlowItems.length}`,
      note: liveFlowItems.length > 0 ? 'Требует наблюдения в реальном времени' : 'Активного пролива сейчас нет',
      tone: liveFlowItems.length > 0 ? 'accent' : 'neutral',
    },
    {
      label: 'Открытые инциденты',
      value: `${openIncidents}`,
      note: `${attentionItems.length} задач в списке внимания`,
      tone: openIncidents > 0 ? 'warning' : 'ok',
    },
    {
      label: 'Сессии сегодня',
      value: `${sessionsToday}`,
      note: `${$visitStore.activeVisits.length} активных визитов сейчас`,
      tone: 'neutral',
    },
    {
      label: 'Объём сегодня',
      value: formatVolumeRu(volumeTodayMl),
      note: nonSaleFlowCount > 0 ? `${nonSaleFlowCount} источника вне продажи` : 'Без внеучётного пролива',
      tone: nonSaleFlowCount > 0 ? 'warning' : 'ok',
    },
    {
      label: 'Выручка сегодня',
      value: formatMinorUnitsRub(revenueToday),
      note: poursToday.length > 0 ? `${poursToday.length} наливов оплачено` : 'Продаж ещё не было',
      tone: 'neutral',
    },
  ];
</script>

<div class="page-header">
  <div>
    <h1>{systemMode ? 'System' : 'Today'}</h1>
    <p class="page-subtitle">{systemMode ? 'Настройки смены, отчёты, API и инженерный контроль рабочего места.' : 'Сначала — situational awareness, затем следующий шаг для оператора.'}</p>
  </div>
  {#if $roleStore.permissions.maintenance_actions}
    <button
      class="emergency-button"
      class:active={$systemStore.emergencyStop}
      on:click={() => (showConfirmModal = true)}
      disabled={$systemStore.loading}
    >
      {#if $systemStore.loading}
        Обработка...
      {:else if $systemStore.emergencyStop}
        Отключить экстренную остановку
      {:else}
        Активировать экстренную остановку
      {/if}
    </button>
  {:else}
    <p class="emergency-note">Роль не позволяет управлять экстренной остановкой.</p>
  {/if}
</div>

{#if systemMode && SHOW_API_BASE_URL}
  <section class="ui-card config-diagnostic">
    <strong>Адрес API:</strong> {$serverConfigStore.baseUrl}
  </section>
{/if}

<section class="top-strip ui-card">
  <article class="top-strip-card shift-overview">
    <span class="eyebrow">Текущая смена</span>
    <strong>{$shiftStore.isOpen ? 'Открыта' : 'Закрыта'}</strong>
    <p>{formatShiftState()}</p>
  </article>

  <article class="top-strip-card time-overview">
    <span class="eyebrow">Текущее время</span>
    <strong>{formatTimeRu(now.toISOString())}</strong>
    <p>{formatDateTimeRu(now.toISOString())}</p>
  </article>

  <article class="top-strip-card health-overview" data-tone={overallHealth}>
    <div class="health-heading">
      <div>
        <span class="eyebrow">Health</span>
        <strong>{statusLabel(overallHealth)}</strong>
      </div>
      <span class="health-badge {overallHealth}">{overallHealth}</span>
    </div>
    <div class="health-pills">
      {#each [backendHealth, controllerHealth, displayAgentHealth] as item}
        <div class="health-pill {healthTone(item.state)}">
          <span>{item.label}</span>
          <strong>{statusLabel(item.state)}</strong>
        </div>
      {/each}
    </div>
  </article>
</section>

<section class="today-layout">
  <div class="primary-column">
    <section class="kpi-grid" aria-label="Сегодняшние KPI">
      {#each todayKpis as kpi}
        <article class="ui-card kpi-card" data-tone={kpi.tone}>
          <span>{kpi.label}</span>
          <strong>{kpi.value}</strong>
          <small>{kpi.note}</small>
        </article>
      {/each}
    </section>

    <section class="ui-card shift-panel">
      <div>
        <h2>Следующее действие по смене</h2>
        <p>{formatShiftState()}</p>
      </div>

      <div class="shift-actions">
        {#if $shiftStore.isOpen}
          <button on:click={closeShift} disabled={$shiftStore.loading}>Закрыть смену</button>
          <button on:click={showXReport} disabled={!$shiftStore.isOpen || $shiftStore.loading}>X-отчёт</button>
        {:else}
          <button on:click={openShift} disabled={$shiftStore.loading}>Открыть смену</button>
          <button on:click={showCurrentZReport} disabled={!canCreateOrShowCurrentZ || $shiftStore.loading}>Показать Z-отчёт</button>
        {/if}
      </div>
    </section>

    <section class="equipment-section">
      <div class="section-header">
        <div>
          <h2>Краны и оборудование</h2>
          <p>Основная рабочая поверхность для оперативного контроля и вмешательства.</p>
        </div>
        <div class="section-summary">
          <span>{activeTaps.length} активных</span>
          <span>{lowKegs.length} кег на исходе</span>
        </div>
      </div>

      {#if $tapStore.loading && $tapStore.taps.length === 0}
        <p>Загрузка статусов кранов...</p>
      {:else if $tapStore.error}
        <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
      {:else}
        <TapGrid taps={$tapStore.taps} />
      {/if}
    </section>

    <section class="secondary-grid">
      <FlowSummaryPanel summary={$pourStore.flowSummary} />

      <aside class="secondary-feed">
        <div class="section-header compact">
          <div>
            <h2>Вторичный блок: лента наливов</h2>
            <p>Для подтверждения контекста, а не как главный action surface.</p>
          </div>
        </div>

        {#if $pourStore.loading && $pourStore.feedItems.length === 0}
          <p>Загрузка ленты наливов...</p>
        {:else if $pourStore.error}
          <p class="error">Ошибка загрузки ленты: {$pourStore.error}</p>
        {:else}
          <PourFeed items={$pourStore.feedItems} />
        {/if}
      </aside>
    </section>
  </div>

  <aside class="attention-column ui-card">
    <div class="attention-header">
      <div>
        <h2>Требует внимания</h2>
        <p>Приоритетный список для next action: от критичного к предупреждениям.</p>
      </div>
      <span class="attention-count">{attentionItems.length}</span>
    </div>

    {#if attentionItems.length === 0}
      <div class="attention-empty">
        <strong>Сейчас всё стабильно.</strong>
        <p>Критичных задач нет, оператор может продолжать мониторинг KPI и ленты наливов.</p>
      </div>
    {:else}
      <div class="attention-list">
        {#each attentionItems as item}
          <article class="alert-row" data-severity={item.severity}>
            <div class="alert-copy">
              <div class="alert-headline">
                <span class="alert-category">{item.category}</span>
                <span class="alert-meta">{item.meta}</span>
              </div>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </div>

            <div class="alert-actions">
              <button class="ghost-action" on:click={() => openAlertTarget(item)}>{item.primaryCta}</button>
              <button class="ghost-action" on:click={() => acknowledgeAlert(item)}>Подтвердить</button>
              <button class="ghost-action subtle" on:click={() => dismissAlert(item.key)}>{item.secondaryCta}</button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </aside>
</section>

{#if systemMode}
  <section class="management-stack">
    {#if $roleStore.permissions.settings_manage}
      <InvestorValuePanel
        taps={$tapStore.taps}
        kegs={$kegStore.kegs}
        pours={$pourStore.pours}
        emergencyStop={$systemStore.emergencyStop}
      />
    {/if}

    <section class="ui-card z-list-panel">
      <div class="z-list-header">
        <div>
          <h2>Management / system</h2>
          <p>X/Z-отчёты и управленческие метрики вынесены ниже операционного слоя.</p>
        </div>
        <button on:click={loadZReports} disabled={zReportsLoading}>Найти</button>
      </div>

      <div class="filters">
        <label>
          С даты
          <input type="date" bind:value={fromDate} />
        </label>
        <label>
          По дату
          <input type="date" bind:value={toDate} />
        </label>
        <div class="report-actions">
          <button on:click={showXReport} disabled={!$shiftStore.isOpen || $shiftStore.loading}>X-отчёт</button>
          <button on:click={createZReport} disabled={!canCreateOrShowCurrentZ || $shiftStore.loading}>Сформировать Z-отчёт</button>
          <button on:click={showCurrentZReport} disabled={!canCreateOrShowCurrentZ || $shiftStore.loading}>Показать Z-отчёт</button>
        </div>
      </div>

      {#if zReportsLoading}
        <p>Загрузка Z-отчётов...</p>
      {:else if zReports.length === 0}
        <p>Z-отчёты не найдены для выбранного диапазона.</p>
      {:else}
        <table class="z-table">
          <thead>
            <tr>
              <th>Сформирован</th>
              <th>Смена</th>
              <th>Объём</th>
              <th>Сумма</th>
              <th>Визиты</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each zReports as item}
              <tr>
                <td>{formatDateTimeRu(item.generated_at)}</td>
                <td>{item.shift_id}</td>
                <td>{formatVolumeRu(item.total_volume_ml)}</td>
                <td>{formatMinorUnitsRub(item.total_amount_cents)}</td>
                <td>{item.active_visits_count}/{item.closed_visits_count}</td>
                <td>
                  <button on:click={() => openReportFromList(item)}>Открыть</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </section>
  </section>
{/if}

{#if showReportModal}
  <Modal on:close={() => (showReportModal = false)}>
    <div slot="header">
      <h2>{reportTitle}</h2>
    </div>
    <ShiftReportView title={reportTitle} payload={reportPayload} reportId={reportId} />
    <div slot="footer" class="modal-actions">
      <button on:click={() => (showReportModal = false)}>Закрыть</button>
    </div>
  </Modal>
{/if}

{#if showConfirmModal}
  <Modal on:close={() => (showConfirmModal = false)}>
    <h2 slot="header">Подтверждение действия</h2>
    <p>
      Вы собираетесь
      <b>{$systemStore.emergencyStop ? 'ОТКЛЮЧИТЬ' : 'АКТИВИРОВАТЬ'}</b>
      режим экстренной остановки.
    </p>
    <p>
      {#if !$systemStore.emergencyStop}
        Это немедленно <b>ЗАБЛОКИРУЕТ</b> все краны и запретит новые наливы.
      {:else}
        Это <b>РАЗБЛОКИРУЕТ</b> систему и вернёт нормальное функционирование.
      {/if}
    </p>
    <p>Вы уверены, что хотите продолжить?</p>
    <div slot="footer" class="modal-actions">
      <button on:click={() => (showConfirmModal = false)}>Отмена</button>
      <button
        class="confirm-button"
        class:danger={!$systemStore.emergencyStop}
        on:click={handleEmergencyStopToggle}
      >
        Да, продолжить
      </button>
    </div>
  </Modal>
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  .page-header h1 { margin: 0; }
  .page-subtitle { margin: 0.35rem 0 0; color: var(--text-secondary); max-width: 720px; }
  .emergency-button {
    background-color: #f0ad4e;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
    font-weight: bold;
  }
  .emergency-button.active { background-color: #d9534f; }
  .emergency-button:disabled { opacity: 0.6; cursor: not-allowed; }
  .emergency-note { color: var(--text-secondary); margin: 0; font-size: 0.9rem; }
  .config-diagnostic { margin-bottom: 1rem; padding: 0.75rem 1rem; }

  .top-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
    padding: 0.75rem;
    margin-bottom: 1rem;
  }
  .top-strip-card {
    border: 1px solid var(--border-soft);
    border-radius: 0.9rem;
    padding: 1rem;
    background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.92));
  }
  .eyebrow {
    display: inline-block;
    margin-bottom: 0.35rem;
    color: var(--text-secondary);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .top-strip-card strong {
    display: block;
    font-size: 1.3rem;
    line-height: 1.15;
  }
  .top-strip-card p {
    margin: 0.4rem 0 0;
    color: var(--text-secondary);
  }
  .health-heading,
  .health-pills,
  .health-pill,
  .section-summary,
  .attention-header,
  .alert-headline,
  .alert-actions,
  .report-actions {
    display: flex;
    gap: 0.5rem;
  }
  .health-heading,
  .attention-header {
    justify-content: space-between;
    align-items: flex-start;
  }
  .health-pills {
    flex-wrap: wrap;
    margin-top: 0.8rem;
  }
  .health-pill,
  .health-badge,
  .attention-count {
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
    font-size: 0.82rem;
    font-weight: 700;
  }
  .health-pill { align-items: center; justify-content: space-between; background: #f8fafc; border: 1px solid var(--border-soft); }
  .health-pill.ok, .health-badge.ok { background: #ecfdf3; color: #166534; }
  .health-pill.warning, .health-badge.warning { background: #fff7ed; color: #9a3412; }
  .health-pill.critical, .health-badge.critical { background: #fef2f2; color: #b91c1c; }

  .today-layout {
    display: grid;
    grid-template-columns: minmax(0, 2.1fr) minmax(320px, 0.9fr);
    gap: 1rem;
    align-items: start;
  }
  .primary-column,
  .management-stack {
    display: grid;
    gap: 1rem;
  }
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.75rem;
  }
  .kpi-card {
    padding: 1rem;
    display: grid;
    gap: 0.35rem;
    border: 1px solid var(--border-soft);
  }
  .kpi-card span,
  .kpi-card small { color: var(--text-secondary); }
  .kpi-card strong { font-size: 1.7rem; line-height: 1.1; }
  .kpi-card[data-tone='warning'] { border-color: #fed7aa; background: #fffaf5; }
  .kpi-card[data-tone='ok'] { border-color: #bbf7d0; background: #f6fff8; }
  .kpi-card[data-tone='accent'] { border-color: #bfdbfe; background: #f8fbff; }

  .shift-panel {
    padding: 1rem;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }
  .shift-panel h2,
  .section-header h2,
  .attention-header h2,
  .z-list-header h2 { margin: 0; }
  .shift-panel p,
  .section-header p,
  .attention-header p,
  .z-list-header p { margin: 0.3rem 0 0; color: var(--text-secondary); }
  .shift-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end; }

  .equipment-section,
  .secondary-feed,
  .attention-column,
  .z-list-panel {
    display: grid;
    gap: 0.9rem;
  }
  .section-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: end;
  }
  .section-summary {
    flex-wrap: wrap;
    justify-content: flex-end;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }
  .secondary-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
    gap: 1rem;
    align-items: start;
  }
  .compact h2 { font-size: 1.1rem; }

  .attention-column {
    padding: 1rem;
    position: sticky;
    top: 0;
  }
  .attention-count {
    background: #111827;
    color: #fff;
  }
  .attention-list {
    display: grid;
    gap: 0.75rem;
  }
  .alert-row {
    border: 1px solid var(--border-soft);
    border-radius: 0.9rem;
    padding: 0.9rem;
    display: grid;
    gap: 0.75rem;
    background: #fff;
  }
  .alert-row[data-severity='critical'] { border-color: #fecaca; background: #fff7f7; }
  .alert-row[data-severity='warning'] { border-color: #fde68a; background: #fffdf5; }
  .alert-copy strong { display: block; margin-top: 0.25rem; }
  .alert-copy p { margin: 0.35rem 0 0; color: var(--text-secondary); }
  .alert-headline {
    justify-content: space-between;
    align-items: center;
    color: var(--text-secondary);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .alert-meta { text-transform: none; letter-spacing: 0; }
  .alert-actions { flex-wrap: wrap; }
  .ghost-action.subtle { opacity: 0.8; }
  .attention-empty {
    border: 1px dashed var(--border-soft);
    border-radius: 0.9rem;
    padding: 1rem;
    background: rgba(248, 250, 252, 0.85);
  }
  .attention-empty strong { display: block; }
  .attention-empty p { margin: 0.35rem 0 0; color: var(--text-secondary); }

  .z-list-panel { padding: 1rem; }
  .z-list-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: end;
  }
  .filters label { display: grid; gap: 0.3rem; font-weight: 600; }
  .report-actions { flex-wrap: wrap; }
  .z-table { width: 100%; border-collapse: collapse; }
  .z-table th, .z-table td { border-bottom: 1px solid var(--border-soft); padding: 0.45rem; text-align: left; }

  .error { color: #c61f35; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 1rem; }
  .confirm-button.danger { background-color: #d9534f; color: white; }

  @media (max-width: 1100px) {
    .top-strip,
    .today-layout,
    .secondary-grid {
      grid-template-columns: 1fr;
    }

    .attention-column {
      position: static;
    }
  }

  @media (max-width: 760px) {
    .page-header,
    .shift-panel,
    .section-header,
    .z-list-header {
      grid-template-columns: 1fr;
      display: grid;
    }

    .health-heading,
    .attention-header,
    .alert-headline {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
