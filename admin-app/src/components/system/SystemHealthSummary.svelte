<script>
  export let summary = { subsystems: [] };
</script>
<div class="system-grid">
  {#each summary.subsystems || [] as subsystem (subsystem.name)}
    <article class={`card ${subsystem.state}`}>
      <div class="head"><h3>{subsystem.name}</h3><span>{subsystem.state}</span></div>
      <p>{subsystem.label}</p>
      {#if subsystem.detail}<small>{subsystem.detail}</small>{/if}
      {#if subsystem.devices?.length}
        <ul>{#each subsystem.devices as device (device.device_id)}<li><strong>{device.tap || device.device_id}</strong><span>{device.label}</span>{#if device.detail}<small>{device.detail}</small>{/if}</li>{/each}</ul>
      {/if}
    </article>
  {/each}
</div>
<style>
  .system-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }
  .card { border: 1px solid #e5e7eb; border-radius: 16px; padding: 1rem; background: #fff; }
  .card.ok { background: #f8fafc; } .card.warning { background: #fffbeb; } .card.critical { background: #fef2f2; }
  .head { display:flex; justify-content:space-between; gap:1rem; align-items:center; }
  h3, p { margin: 0; } ul { margin: 0.75rem 0 0; padding-left: 1rem; } li { margin-bottom: 0.45rem; } small { display:block; color: var(--text-secondary); }
</style>
