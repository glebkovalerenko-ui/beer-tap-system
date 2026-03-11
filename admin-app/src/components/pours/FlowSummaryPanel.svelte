<script>
  import { formatVolumeRu } from '../../lib/formatters.js';

  export let summary = null;

  const reasonLabels = {
    closed_valve_no_card: 'Закрытый клапан без карты',
    closed_valve_no_session: 'Закрытый клапан без валидной сессии',
    closed_valve_no_valid_session: 'Закрытый клапан вне валидной сессии',
    controller_flow_anomaly: 'Прочая flow-анomaly',
  };

  function labelForReason(reasonCode) {
    return reasonLabels[reasonCode] || reasonCode;
  }
</script>

<section class="flow-summary ui-card">
  <div class="header">
    <div>
      <h2>Сводка flow</h2>
      <p>Продажа и flow вне продажи считаются отдельно, но сходятся в общий физический пролив.</p>
    </div>
  </div>

  {#if summary}
    <div class="totals-grid">
      <article>
        <span>По продаже</span>
        <strong>{formatVolumeRu(summary.sale_volume_ml)}</strong>
      </article>
      <article>
        <span>Вне продажи</span>
        <strong>{formatVolumeRu(summary.non_sale_volume_ml)}</strong>
      </article>
      <article>
        <span>Общий пролив</span>
        <strong>{formatVolumeRu(summary.total_volume_ml)}</strong>
      </article>
    </div>

    <div class="summary-grid">
      <section>
        <h3>По кранам</h3>
        {#if summary.by_tap?.length}
          <div class="tap-list">
            {#each summary.by_tap as tap}
              <article class="tap-card">
                <div class="tap-title">
                  <strong>{tap.tap_name || `Кран #${tap.tap_id}`}</strong>
                  <span>Итого {formatVolumeRu(tap.total_volume_ml)}</span>
                </div>
                <dl>
                  <div>
                    <dt>Продажа</dt>
                    <dd>{formatVolumeRu(tap.sale_volume_ml)}</dd>
                  </div>
                  <div>
                    <dt>Вне продажи</dt>
                    <dd>{formatVolumeRu(tap.non_sale_volume_ml)}</dd>
                  </div>
                </dl>
              </article>
            {/each}
          </div>
        {:else}
          <p class="muted">Нет данных по кранам.</p>
        {/if}
      </section>

      <section>
        <h3>Причины вне продажи</h3>
        {#if summary.non_sale_breakdown?.length}
          <ul class="breakdown-list">
            {#each summary.non_sale_breakdown as item}
              <li>
                <span>{labelForReason(item.reason_code)}</span>
                <strong>{formatVolumeRu(item.volume_ml)}</strong>
              </li>
            {/each}
          </ul>
        {:else}
          <p class="muted">Сейчас non-sale flow не зафиксирован.</p>
        {/if}
      </section>
    </div>
  {:else}
    <p class="muted">Сводка flow загружается.</p>
  {/if}
</section>

<style>
  .flow-summary {
    display: grid;
    gap: 1rem;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  .header h2, .summary-grid h3 {
    margin: 0;
  }
  .header p {
    margin: 0.35rem 0 0;
    color: var(--text-secondary);
  }
  .totals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
  }
  .totals-grid article,
  .tap-card {
    border: 1px solid var(--border-soft);
    border-radius: 0.75rem;
    padding: 0.85rem;
    background: rgba(255, 255, 255, 0.72);
  }
  .totals-grid span,
  dt,
  .tap-title span {
    color: var(--text-secondary);
    font-size: 0.9rem;
  }
  .totals-grid strong,
  .tap-title strong {
    display: block;
    margin-top: 0.35rem;
  }
  .summary-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1rem;
  }
  .tap-list,
  .breakdown-list {
    display: grid;
    gap: 0.65rem;
  }
  .tap-title,
  .breakdown-list li,
  dl div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
  }
  dl {
    display: grid;
    gap: 0.4rem;
    margin: 0.75rem 0 0;
  }
  dt, dd {
    margin: 0;
  }
  .breakdown-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .breakdown-list li {
    border-bottom: 1px solid var(--border-soft);
    padding-bottom: 0.5rem;
  }
  .breakdown-list li:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
  .muted {
    margin: 0.5rem 0 0;
    color: var(--text-secondary);
  }

  @media (max-width: 900px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
