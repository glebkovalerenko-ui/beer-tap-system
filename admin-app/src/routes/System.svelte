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

  function formatBlockedActionKey(value) {
    if (!value) return 'Unknown action';
    const text = String(value).replaceAll('_', ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
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
        ? ($operatorConnectionStore.reason || $systemStore.reason || 'Backend currently degraded. Risky actions stay blocked until fresh data returns.')
        : ''
    );
    return {
      key,
      label: formatBlockedActionKey(key),
      available: !state.disabled,
      reason: state.reason || (state.disabled
        ? 'Wait for a fresh system snapshot before using this action.'
        : 'This action can be used in the current context.'),
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
    <h1>System</h1>
    <p>This operational health section is available only to roles with system health permissions.</p>
  </section>
{:else}
  <section class="page">
    <div class="page-header">
      <div>
        <h1>{ROUTE_COPY.system.title}</h1>
        <p>{ROUTE_COPY.system.description} Deep engineering actions and settings remain permission-gated.</p>
      </div>
      <DataFreshnessChip
        label="System"
        lastFetchedAt={$systemStore.lastFetchedAt}
        staleAfterMs={$systemStore.staleTtlMs}
        mode={$operatorConnectionStore.mode}
        transport={$operatorConnectionStore.transport}
        reason={$operatorConnectionStore.reason || $systemStore.reason}
      />
    </div>

    {#if incidentFocusSource}
      <div class="ui-card incident-context">Opened from incident context: check source <strong>{incidentFocusSource}</strong> first, then inspect related devices and sync queues.</div>
    {/if}

    {#if $operatorConnectionStore.readOnly}
      <section class="ui-card degraded-panel">
        <strong>Read-only mode</strong>
        <p>{$operatorConnectionStore.reason || $systemStore.reason || 'Backend currently degraded. Risky actions stay blocked until fresh data returns.'}</p>
      </section>
    {/if}

    <div class="hero-grid">
      <section class="ui-card panel hero-card">
        <div class="hero">
          <div><span class="eyebrow">Overall state</span><strong>{$systemStore.health.overall === 'ok' ? 'Operating normally' : 'Needs operator attention'}</strong></div>
          <div><span class="eyebrow">Mode</span><strong>{$systemStore.mode || 'online'}</strong></div>
          <div><span class="eyebrow">Open incidents</span><strong>{$systemStore.openIncidentCount}</strong></div>
          <div><span class="eyebrow">Emergency stop</span><strong>{$systemStore.emergencyStop ? 'Enabled' : 'Disabled'}</strong></div>
        </div>
      </section>

      <section class="ui-card panel hero-card">
        <div class="hero">
          <div><span class="eyebrow">Queue backlog</span><strong>{$systemStore.queueSummary?.pending_items || 0}</strong></div>
          <div><span class="eyebrow">Unsynced sessions</span><strong>{$systemStore.queueSummary?.unsynced_sessions || 0}</strong></div>
          <div><span class="eyebrow">Oldest pending</span><strong>{$systemStore.queueSummary?.oldest_pending_age_seconds != null ? `${Math.round($systemStore.queueSummary.oldest_pending_age_seconds)} s` : '-'}</strong></div>
          <div><span class="eyebrow">Stale devices</span><strong>{$systemStore.staleSummary?.stale_device_count || 0}</strong></div>
        </div>
      </section>
    </div>

      <section class="ui-card panel">
      <div class="section-head">
        <div>
          <h2>What is blocked right now</h2>
          <p>This section shows not only health state, but which actions are unsafe until backend freshness returns.</p>
        </div>
      </div>
      <div class="blocked-grid">
        {#each blockedActions as action (action.key)}
          <article class="blocked-item">
            <span>{action.label}</span>
            <strong>{action.available ? 'Available' : 'Blocked'}</strong>
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
