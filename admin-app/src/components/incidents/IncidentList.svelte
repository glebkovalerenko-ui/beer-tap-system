<script>
  import { formatDateTimeRu } from '../../lib/formatters.js';
  export let items = [];
  const priorityLabels = { low: 'Low', medium: 'Medium', high: 'High', critical: 'Critical' };
  const statusLabels = { new: 'New', in_progress: 'In progress', closed: 'Closed' };
</script>
<div class="incident-list">
  {#if items.length === 0}
    <p class="empty">Нет агрегированных инцидентов.</p>
  {:else}
    <table>
      <thead><tr><th>Priority</th><th>Created</th><th>Tap</th><th>Type</th><th>Status</th><th>Operator</th><th>Note / action</th></tr></thead>
      <tbody>
        {#each items as item (item.incident_id)}
          <tr>
            <td><span class={`pill ${item.priority}`}>{priorityLabels[item.priority] || item.priority}</span></td>
            <td>{formatDateTimeRu(item.created_at)}</td><td>{item.tap || '—'}</td><td>{item.type}</td>
            <td>{statusLabels[item.status] || item.status}</td><td>{item.operator || '—'}</td><td>{item.note_action || '—'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>
<style>
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
  th { font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); }
  .pill { display: inline-flex; padding: 0.25rem 0.55rem; border-radius: 999px; font-weight: 700; font-size: 0.78rem; }
  .low { background: #e2e8f0; } .medium { background: #dbeafe; color: #1d4ed8; } .high { background: #fef3c7; color: #92400e; } .critical { background: #fee2e2; color: #b91c1c; }
  .empty { color: var(--text-secondary); }
</style>
