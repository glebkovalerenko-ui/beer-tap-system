<script>
  import { onMount } from 'svelte';

  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import SystemHealthSummary from '../components/system/SystemHealthSummary.svelte';
  import { resolveActionBlockState } from '../lib/operator/actionPolicyAdapter.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';

  let incidentFocusSource = '';

  /** @type {{ canViewHealth: boolean, canUseEngineeringActions: boolean, canManageSystemSettings: boolean }} */
  let systemPermissions = {
    canViewHealth: false,
    canUseEngineeringActions: false,
    canManageSystemSettings: false,
  };

  /** @type {any} */
  let permissions = {};

  const READ_ONLY_FALLBACK = 'Данные устарели или центральный контур недоступен. Рискованные действия останутся заблокированы, пока не вернётся свежая сводка.';

  function formatBlockedActionKey(value) {
    if (!value) return 'Неизвестное действие';
    const text = String(value).replaceAll('_', ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function formatModeLabel(value) {
    const key = String(value || '').trim().toLowerCase();
    if (!key || key === 'online') return 'Онлайн';
    if (key === 'offline') return 'Офлайн';
    if (key === 'degraded') return 'С деградацией';
    if (key === 'read_only' || key === 'readonly') return 'Только просмотр';
    if (key === 'demo') return 'Демо';
    return value;
  }

  function formatSeconds(value) {
    if (value == null || Number.isNaN(Number(value))) return '—';
    return `${Math.round(Number(value))} с`;
  }

  $: permissions = /** @type {any} */ ($roleStore.permissions || {});
  $: systemPermissions = {
    canViewHealth: Boolean(permissions.system_health_view),
    canUseEngineeringActions: Boolean(permissions.system_engineering_actions),
    canManageSystemSettings: Boolean(permissions.settings_manage),
  };
  $: blockedActions = Object.entries($systemStore.blockedActions || {}).map(([key, policy]) => {
    const state = resolveActionBlockState(
      policy,
      $operatorConnectionStore.readOnly
        ? ($operatorConnectionStore.reason || $systemStore.reason || READ_ONLY_FALLBACK)
        : ''
    );
    return {
      key,
      label: formatBlockedActionKey(key),
      available: !state.disabled,
      reason: state.reason || (state.disabled
        ? 'Дождитесь свежей сводки по системе перед выполнением этого действия.'
        : 'Действие доступно в текущем состоянии системы.'),
    };
  });

  onMount(() => {
    incidentFocusSource = sessionStorage.getItem('system.focusSource') || '';
    if (incidentFocusSource) {
      sessionStorage.removeItem('system.focusSource');
    }
  });
</script>

{#if !systemPermissions.canViewHealth}
  <section class="ui-card restricted">
    <h1>{ROUTE_COPY.system.title}</h1>
    <p>Раздел доступен ролям, которым разрешено смотреть состояние системы и очереди синхронизации.</p>
  </section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>{ROUTE_COPY.system.title}</h1>
        <p>{ROUTE_COPY.system.description} Инженерные действия и глубокие настройки вынесены в отдельный блок по правам.</p>
      </div>
      <DataFreshnessChip
        label="Система"
        lastFetchedAt={$systemStore.lastFetchedAt}
        staleAfterMs={$systemStore.staleTtlMs}
        mode={$operatorConnectionStore.mode}
        transport={$operatorConnectionStore.transport}
        reason={$operatorConnectionStore.reason || $systemStore.reason}
      />
    </div>

    {#if incidentFocusSource}
      <div class="ui-card incident-context">Открыто из инцидента: сначала проверьте источник <strong>{incidentFocusSource}</strong>, затем связанные устройства и очередь синхронизации.</div>
    {/if}

    {#if $operatorConnectionStore.readOnly}
      <section class="ui-card degraded-panel">
        <strong>Только просмотр.</strong>
        <p>{$operatorConnectionStore.reason || $systemStore.reason || READ_ONLY_FALLBACK}</p>
      </section>
    {/if}

    <div class="hero-grid">
      <section class="ui-card panel hero-card">
        <div class="hero">
          <div><span class="eyebrow">Общее состояние</span><strong>{$systemStore.health.overall === 'ok' ? 'Работает штатно' : 'Нужно внимание'}</strong></div>
          <div><span class="eyebrow">Режим работы</span><strong>{formatModeLabel($systemStore.mode)}</strong></div>
          <div><span class="eyebrow">Открытые инциденты</span><strong>{$systemStore.openIncidentCount}</strong></div>
          <div><span class="eyebrow">Аварийная остановка</span><strong>{$systemStore.emergencyStop ? 'Включена' : 'Выключена'}</strong></div>
        </div>
      </section>

      <section class="ui-card panel hero-card">
        <div class="hero">
          <div><span class="eyebrow">Очередь обмена</span><strong>{$systemStore.queueSummary?.pending_items || 0}</strong></div>
          <div><span class="eyebrow">Несинхронизированные визиты</span><strong>{$systemStore.queueSummary?.unsynced_sessions || 0}</strong></div>
          <div><span class="eyebrow">Старейшая задержка</span><strong>{formatSeconds($systemStore.queueSummary?.oldest_pending_age_seconds)}</strong></div>
          <div><span class="eyebrow">Устройства без свежих данных</span><strong>{$systemStore.staleSummary?.stale_device_count || 0}</strong></div>
        </div>
      </section>
    </div>

    <section class="ui-card panel">
      <div class="section-head">
        <div>
          <h2>Что может мешать работе точки</h2>
          <p>Здесь видно не только общее состояние, но и какие действия лучше отложить до возврата свежих данных.</p>
        </div>
      </div>
      <div class="blocked-grid">
        {#each blockedActions as action (action.key)}
          <article class="blocked-item">
            <span>{action.label}</span>
            <strong>{action.available ? 'Доступно' : 'Заблокировано'}</strong>
            <p>{action.reason}</p>
          </article>
        {/each}
      </div>
      <ul class="next-steps">
        {#each $systemStore.actionableNextSteps || [] as step}
          <li>{step}</li>
        {/each}
      </ul>
    </section>

    <SystemHealthSummary
      summary={$systemStore}
      canUseEngineeringActions={systemPermissions.canUseEngineeringActions}
      canManageSystemSettings={systemPermissions.canManageSystemSettings}
    />
  </section>
{/if}

<style>
  .restricted, .panel { padding: 1rem; }
  .page { display: grid; gap: 1rem; }
  .page-header, .section-head { display: flex; justify-content: space-between; gap: 1rem; align-items: start; flex-wrap: wrap; }
  .page-header h1, .page-header p, .section-head h2, .section-head p { margin: 0; }
  .page-header { gap: 0.75rem 1rem; }
  .hero-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .hero { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
  .eyebrow { display: block; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; }
  .incident-context { padding: 0.85rem 1rem; border: 1px solid #bfdbfe; border-radius: 12px; background: #eff6ff; color: #1e3a8a; }
  .degraded-panel { border: 1px solid #fcd34d; background: #fff7ed; color: #9a3412; padding: 1rem; display: grid; gap: 0.35rem; }
  .degraded-panel p { margin: 0; }
  .blocked-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; }
  .blocked-item { border: 1px solid #e5e7eb; border-radius: 14px; padding: 0.85rem; display: grid; gap: 0.3rem; background: #fff; }
  .blocked-item p { margin: 0; color: var(--text-secondary); }
  .next-steps { margin: 0; padding-left: 1.25rem; display: grid; gap: 0.4rem; }
  @media (max-width: 860px) {
    .hero-grid, .hero { grid-template-columns: 1fr; }
  }
</style>
