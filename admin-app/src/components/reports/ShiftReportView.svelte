<script>
  export let payload = null;
  export let title = 'Отчёт смены';
  export let reportId = null;
</script>

<section class="report-view">
  <h2>{title}</h2>
  {#if reportId}
    <p class="meta-line"><strong>ID отчёта:</strong> {reportId}</p>
  {/if}

  {#if !payload}
    <p>Нет данных отчёта.</p>
  {:else}
    <div class="grid">
      <div class="card">
        <h3>Метаданные</h3>
        <p><strong>Смена:</strong> {payload.meta?.shift_id || '—'}</p>
        <p><strong>Тип:</strong> {payload.meta?.report_type || '—'}</p>
        <p><strong>Сформирован:</strong> {payload.meta?.generated_at ? new Date(payload.meta.generated_at).toLocaleString() : '—'}</p>
        <p><strong>Открыта:</strong> {payload.meta?.opened_at ? new Date(payload.meta.opened_at).toLocaleString() : '—'}</p>
        <p><strong>Закрыта:</strong> {payload.meta?.closed_at ? new Date(payload.meta.closed_at).toLocaleString() : '—'}</p>
      </div>

      <div class="card">
        <h3>Итоги</h3>
        <p><strong>Наливов:</strong> {payload.totals?.pours_count ?? 0}</p>
        <p><strong>Объём (мл):</strong> {payload.totals?.total_volume_ml ?? 0}</p>
        <p><strong>Сумма (коп):</strong> {payload.totals?.total_amount_cents ?? 0}</p>
        <p><strong>Новых гостей:</strong> {payload.totals?.new_guests_count ?? 0}</p>
        <p><strong>pending_sync:</strong> {payload.totals?.pending_sync_count ?? 0}</p>
        <p><strong>reconciled:</strong> {payload.totals?.reconciled_count ?? 0}</p>
        <p><strong>mismatch:</strong> {payload.totals?.mismatch_count ?? 0}</p>
      </div>
    </div>

    <div class="card">
      <h3>Визиты</h3>
      <p><strong>Активные:</strong> {payload.visits?.active_visits_count ?? 0}</p>
      <p><strong>Закрытые:</strong> {payload.visits?.closed_visits_count ?? 0}</p>
    </div>

    <div class="card">
      <h3>По кранам</h3>
      {#if (payload.by_tap || []).length === 0}
        <p>Нет данных по кранам.</p>
      {:else}
        <table>
          <thead>
            <tr>
              <th>Кран</th>
              <th>Наливов</th>
              <th>Объём (мл)</th>
              <th>Сумма (коп)</th>
              <th>pending_sync</th>
            </tr>
          </thead>
          <tbody>
            {#each payload.by_tap as item}
              <tr>
                <td>{item.tap_id}</td>
                <td>{item.pours_count}</td>
                <td>{item.volume_ml}</td>
                <td>{item.amount_cents}</td>
                <td>{item.pending_sync_count}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <div class="card">
      <h3>Кеги</h3>
      <p><strong>Статус:</strong> {payload.kegs?.status || 'not_available_yet'}</p>
      <p>{payload.kegs?.note || 'Will be added when keg<->pour linkage is implemented'}</p>
    </div>
  {/if}
</section>

<style>
  .report-view { display: grid; gap: 0.75rem; }
  .report-view h2 { margin: 0; }
  .meta-line { margin: 0; color: var(--text-secondary); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 0.75rem; }
  .card {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 0.75rem;
    background: var(--bg-surface-muted);
  }
  .card h3 { margin-top: 0; margin-bottom: 0.5rem; }
  .card p { margin: 0.25rem 0; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border-bottom: 1px solid var(--border-soft); padding: 0.4rem; text-align: left; }
</style>
