<script>
  // @ts-nocheck
  import { onMount } from 'svelte';
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import SystemHealthSummary from '../components/system/SystemHealthSummary.svelte';

  let incidentFocusSource = '';

  onMount(() => {
    incidentFocusSource = sessionStorage.getItem('system.focusSource') || '';
    if (incidentFocusSource) {
      sessionStorage.removeItem('system.focusSource');
    }
  });
</script>

{#if !$roleStore.permissions.system_view}
  <section class="ui-card restricted"><h1>Система</h1><p>Раздел настроек и инженерных инструментов доступен только инженерным ролям.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <h1>Система</h1>
      <p>Сводка по состоянию сервера, базы данных, контроллеров, экранов, считывателей и очередей обмена.</p>
    </div>
    <div class="ui-card panel">
      {#if incidentFocusSource}
        <div class="incident-context">Открыто из инцидента: проверьте источник <strong>{incidentFocusSource}</strong> и связанные subsystem/device карточки.</div>
      {/if}
      <div class="hero">
        <div><span class="eyebrow">Общее состояние</span><strong>{$systemStore.overallState}</strong></div>
        <div><span class="eyebrow">Открытые инциденты</span><strong>{$systemStore.openIncidentCount}</strong></div>
        <div><span class="eyebrow">Экстренная остановка</span><strong>{$systemStore.emergencyStop ? 'Включена' : 'Выключена'}</strong></div>
      </div>
    </div>
    <SystemHealthSummary summary={$systemStore} />
  </section>
{/if}

<style>.restricted,.panel{padding:1rem}.page{display:grid;gap:1rem}.page-header h1,.page-header p{margin:0}.hero{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.eyebrow{display:block;color:var(--text-secondary);font-size:.8rem;text-transform:uppercase}.incident-context{margin-bottom:1rem;padding:.85rem 1rem;border:1px solid #bfdbfe;border-radius:12px;background:#eff6ff;color:#1e3a8a}</style>
