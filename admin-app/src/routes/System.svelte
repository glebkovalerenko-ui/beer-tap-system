<script>
  import { roleStore } from '../stores/roleStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import SystemHealthSummary from '../components/system/SystemHealthSummary.svelte';
</script>

{#if !$roleStore.permissions.system}
  <section class="ui-card restricted"><h1>System</h1><p>Раздел настроек и инженерных инструментов доступен только роли engineer_owner.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <h1>System</h1>
      <p>Operational summary по backend, database, controllers, display agents, readers и sync queue.</p>
    </div>
    <div class="ui-card panel">
      <div class="hero">
        <div><span class="eyebrow">Overall</span><strong>{$systemStore.overallState}</strong></div>
        <div><span class="eyebrow">Open incidents</span><strong>{$systemStore.openIncidentCount}</strong></div>
        <div><span class="eyebrow">Emergency stop</span><strong>{$systemStore.emergencyStop ? 'ON' : 'OFF'}</strong></div>
      </div>
    </div>
    <SystemHealthSummary summary={$systemStore} />
  </section>
{/if}

<style>.restricted,.panel{padding:1rem}.page{display:grid;gap:1rem}.page-header h1,.page-header p{margin:0}.hero{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.eyebrow{display:block;color:var(--text-secondary);font-size:.8rem;text-transform:uppercase}</style>
