<script>
  import { onMount } from 'svelte';
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import SystemHealthSummary from '../components/system/SystemHealthSummary.svelte';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';

  let incidentFocusSource = '';

  
  /** @type {{ canViewHealth: boolean, canUseEngineeringActions: boolean, canManageSystemSettings: boolean }} */
  let systemPermissions = {
    canViewHealth: false,
    canUseEngineeringActions: false,
    canManageSystemSettings: false,
  };

  /** @type {any} */
  let permissions = {};

  $: permissions = /** @type {any} */ ($roleStore.permissions || {});
  $: systemPermissions = {
    canViewHealth: Boolean(permissions.system_health_view),
    canUseEngineeringActions: Boolean(permissions.system_engineering_actions),
    canManageSystemSettings: Boolean(permissions.settings_manage),
  };

  onMount(() => {
    incidentFocusSource = sessionStorage.getItem('system.focusSource') || '';
    if (incidentFocusSource) {
      sessionStorage.removeItem('system.focusSource');
    }
  });
</script>

{#if !systemPermissions.canViewHealth}
  <section class="ui-card restricted">
    <h1>Система</h1>
    <p>Раздел с operational health, устройствами и синхронизацией доступен оператору, старшему смены и инженеру по назначенным правам.</p>
  </section>
{:else}
  <section class="page">
    <div class="page-header">
      <h1>{ROUTE_COPY.system.title}</h1>
      <p>{ROUTE_COPY.system.description} Глубокие инженерные действия и настройки остаются отдельным permission-gated слоем.</p>
    </div>
    <div class="ui-card panel">
      {#if incidentFocusSource}
        <div class="incident-context">Открыто из инцидента: сначала проверьте источник <strong>{incidentFocusSource}</strong>, затем состояние связанных устройств и очередей обмена.</div>
      {/if}
      <div class="hero">
        <div><span class="eyebrow">Общий статус</span><strong>{$systemStore.health.overall === 'ok' ? 'Работаем штатно' : 'Нужно внимание смены'}</strong></div>
        <div><span class="eyebrow">Открытые инциденты</span><strong>{$systemStore.openIncidentCount}</strong></div>
        <div><span class="eyebrow">Экстренная остановка</span><strong>{$systemStore.emergencyStop ? 'Включена' : 'Выключена'}</strong></div>
      </div>
    </div>
    <SystemHealthSummary
      summary={$systemStore}
      canUseEngineeringActions={systemPermissions.canUseEngineeringActions}
      canManageSystemSettings={systemPermissions.canManageSystemSettings}
    />
  </section>
{/if}

<style>
  .restricted,.panel{padding:1rem}
  .page{display:grid;gap:1rem}
  .page-header h1,.page-header p{margin:0}
  .page-header{display:grid;gap:.35rem}
  .hero{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}
  .eyebrow{display:block;color:var(--text-secondary);font-size:.8rem;text-transform:uppercase}
  .incident-context{margin-bottom:1rem;padding:.85rem 1rem;border:1px solid #bfdbfe;border-radius:12px;background:#eff6ff;color:#1e3a8a}
  @media (max-width: 860px){.hero{grid-template-columns:1fr}}
</style>
