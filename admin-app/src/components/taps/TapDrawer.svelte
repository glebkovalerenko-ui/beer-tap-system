<script>
  import { createEventDispatcher } from 'svelte';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../../lib/formatters.js';

  export let tap;
  export let canDisplayOverride = false;

  const dispatch = createEventDispatcher();

  $: operations = tap?.operations || {};
  $: session = operations.activeSessionSummary;
  $: events = operations.recentEvents || [];
</script>

{#if tap}
  <aside class="tap-drawer">
    <div class="drawer-head">
      <div>
        <div class="eyebrow">Tap detail</div>
        <h2>{tap.display_name}</h2>
        <p>{operations.productStateLabel} · {operations.liveStatus}</p>
      </div>
      <button class="close-btn" on:click={() => dispatch('close')}>✕</button>
    </div>

    <section class="drawer-section stats-grid">
      <article>
        <span>Heartbeat</span>
        <strong>{operations.heartbeat?.at ? formatDateTimeRu(operations.heartbeat.at) : 'Нет данных'}</strong>
        <small>{operations.heartbeat?.minutesAgo != null ? `${operations.heartbeat.minutesAgo} мин назад` : 'Источник не передал heartbeat'}</small>
      </article>
      <article>
        <span>Sync state</span>
        <strong>{operations.syncState?.label || 'Нет данных'}</strong>
        <small>{tap.status}</small>
      </article>
      <article>
        <span>Текущий налив</span>
        <strong>{formatVolumeRu(operations.currentPour?.volumeMl || 0)}</strong>
        <small>{operations.currentPour?.amount ? formatRubAmount(operations.currentPour.amount) : 'Без списания'}</small>
      </article>
    </section>

    <section class="drawer-section info-grid">
      <article>
        <h3>Оперативный статус</h3>
        <dl>
          <div><dt>Product state</dt><dd>{operations.productStateLabel}</dd></div>
          <div><dt>Controller</dt><dd>{operations.controllerStatus?.label || 'Нет данных'}</dd></div>
          <div><dt>Display</dt><dd>{operations.displayStatus?.label || 'Нет данных'}</dd></div>
          <div><dt>Reader</dt><dd>{operations.readerStatus?.label || 'Нет данных'}</dd></div>
        </dl>
      </article>
      <article>
        <h3>Гость / карта</h3>
        <dl>
          <div><dt>Активный гость</dt><dd>{session?.guestName || 'Нет активной сессии'}</dd></div>
          <div><dt>Карта</dt><dd>{session?.cardUid || '—'}</dd></div>
          <div><dt>Баланс</dt><dd>{session?.balance ? formatRubAmount(session.balance) : '—'}</dd></div>
          <div><dt>Открыта</dt><dd>{session?.openedAt ? formatDateTimeRu(session.openedAt) : '—'}</dd></div>
        </dl>
      </article>
    </section>

    <section class="drawer-section">
      <div class="section-head">
        <div>
          <h3>Последние события крана</h3>
          <p>События берутся из live feed и локального снапшота крана.</p>
        </div>
        {#if canDisplayOverride}
          <button class="secondary-btn" on:click={() => dispatch('display-settings', { tap })}>Настройки экрана</button>
        {/if}
      </div>

      {#if events.length}
        <ul class="events-list">
          {#each events as item, index}
            <li>
              <div>
                <strong>{item.item_type === 'pour' ? 'Продажа' : 'Flow event'} #{index + 1}</strong>
                <p>{item.reason || item.event_status || item.status || 'Без кода события'}</p>
              </div>
              <div class="event-meta">
                <span>{formatDateTimeRu(item.ended_at || item.timestamp || item.created_at)}</span>
                <span>{formatVolumeRu(item.volume_ml || 0)}</span>
              </div>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Нет недавних событий по этому крану.</p>
      {/if}
    </section>
  </aside>
{/if}

<style>
  .tap-drawer { width: min(720px, 92vw); max-height: 88vh; overflow: auto; display: grid; gap: 1rem; }
  .drawer-head, .section-head, .event-meta, .events-list li, .stats-grid, .info-grid { display: flex; gap: 1rem; }
  .drawer-head, .section-head, .events-list li { justify-content: space-between; align-items: flex-start; }
  .drawer-head h2, .drawer-section h3, .drawer-head p { margin: 0; }
  .eyebrow, .muted, small, dt, .section-head p { color: var(--text-secondary, #64748b); }
  .close-btn, .secondary-btn { border-radius: 10px; border: 1px solid #cbd5e1; background: #fff; padding: 0.6rem 0.8rem; font-weight: 600; }
  .drawer-section { border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; background: rgba(248,250,252,0.8); display: grid; gap: 0.8rem; }
  .stats-grid, .info-grid { flex-wrap: wrap; }
  .stats-grid article, .info-grid article { flex: 1 1 220px; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 0.9rem; }
  dl { display: grid; gap: 0.6rem; margin: 0.75rem 0 0; }
  dl div { display: flex; justify-content: space-between; gap: 1rem; }
  dt, dd { margin: 0; }
  .events-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.65rem; }
  .events-list li { border: 1px solid #e2e8f0; border-radius: 14px; padding: 0.8rem; background: #fff; }
  .events-list p { margin: 0.2rem 0 0; color: var(--text-secondary, #64748b); }
  .event-meta { flex-direction: column; align-items: flex-end; color: var(--text-secondary, #64748b); font-size: 0.84rem; }
</style>
