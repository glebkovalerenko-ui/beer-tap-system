<script>
  import { createEventDispatcher } from 'svelte';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../../lib/formatters.js';

  export let tap;
  export let canDisplayOverride = false;
  export let canControl = false;

  const dispatch = createEventDispatcher();

  $: operations = tap?.operations || {};
  $: session = operations.activeSessionSummary;
  $: currentPour = operations.currentPour || {};
  $: operatorHistory = operations.operatorHistory || [];
  $: isLocked = tap?.status === 'locked';

  function emit(name) {
    dispatch(name, { tap });
  }

  function openLinkedSession(visitId) {
    dispatch('open-session', { tap, visitId: visitId || session?.visitId || null });
  }
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
        <strong>{formatVolumeRu(currentPour.volumeMl || 0)}</strong>
        <small>{currentPour.amount ? formatRubAmount(currentPour.amount) : 'Без списания'}</small>
      </article>
    </section>

    <section class="drawer-section current-session">
      <div class="section-head">
        <div>
          <h3>Текущая сессия</h3>
          <p>Явные операторские действия по активной блокировке и текущему наливу.</p>
        </div>
      </div>

      <div class="session-panel">
        <div class="session-copy">
          <strong>{session?.guestName || 'Сессия сейчас не открыта'}</strong>
          <p>
            {#if session}
              Карта {session.cardUid || 'не привязана'} · открыта {session.openedAt ? formatDateTimeRu(session.openedAt) : 'недавно'}
            {:else}
              Откройте сессию, если гость уже у крана, или заблокируйте линию до начала работы.
            {/if}
          </p>
          <div class="session-metrics">
            <span>Налито: {formatVolumeRu(currentPour.volumeMl || 0)}</span>
            <span>Сумма: {currentPour.amount ? formatRubAmount(currentPour.amount) : '0 ₽'}</span>
            <span>Статус: {currentPour.isActive ? 'Налив активен' : 'Поток не зафиксирован'}</span>
          </div>
        </div>

        <div class="action-stack">
          {#if canControl && session}
            <button class="primary danger" on:click={() => emit('stop-pour')}>Остановить налив</button>
          {/if}
          <button class="primary" on:click={() => openLinkedSession(session?.visitId)}>Открыть сессию</button>
          {#if canControl}
            <button class="secondary" on:click={() => emit('toggle-lock')}>
              {isLocked ? 'Разблокировать кран' : 'Заблокировать кран'}
            </button>
          {/if}
        </div>
      </div>
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
          <h3>История действий оператора</h3>
          <p>Последние события уже преобразованы в человекочитаемую ленту со ссылками на сессию и инцидент.</p>
        </div>
        {#if canDisplayOverride}
          <button class="secondary-btn" on:click={() => dispatch('display-settings', { tap })}>Настройки экрана</button>
        {/if}
      </div>

      {#if operatorHistory.length}
        <ul class="events-list">
          {#each operatorHistory as item}
            <li class={`tone-${item.tone}`}>
              <div class="event-main">
                <div class="event-headline">
                  <strong>{item.title}</strong>
                  <span class={`priority ${item.tone}`}>{item.priorityLabel}</span>
                </div>
                <p>{item.description}</p>
                <div class="event-links">
                  {#if item.sessionAction}
                    <a href={item.sessionAction.href} on:click|preventDefault={() => openLinkedSession(item.sessionAction.visitId)}>
                      {item.sessionAction.label}
                    </a>
                  {/if}
                  {#if item.incidentAction}
                    <a href={item.incidentAction.href}>{item.incidentAction.label}</a>
                  {/if}
                </div>
              </div>
              <div class="event-meta">
                <span>{item.happenedAt ? formatDateTimeRu(item.happenedAt) : 'Время неизвестно'}</span>
                <span>{formatVolumeRu(item.volumeMl || 0)}</span>
                <span>{item.amount ? formatRubAmount(item.amount) : item.rawStatus || 'Без суммы'}</span>
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
  .drawer-head, .section-head, .event-meta, .events-list li, .stats-grid, .info-grid, .session-panel { display: flex; gap: 1rem; }
  .drawer-head, .section-head, .events-list li { justify-content: space-between; align-items: flex-start; }
  .drawer-head h2, .drawer-section h3, .drawer-head p { margin: 0; }
  .eyebrow, .muted, small, dt, .section-head p, .session-copy p { color: var(--text-secondary, #64748b); }
  .close-btn, .secondary-btn, .primary, .secondary { border-radius: 10px; border: 1px solid #cbd5e1; background: #fff; padding: 0.6rem 0.8rem; font-weight: 600; }
  .drawer-section { border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; background: rgba(248,250,252,0.8); display: grid; gap: 0.8rem; }
  .stats-grid, .info-grid, .session-panel { flex-wrap: wrap; }
  .stats-grid article, .info-grid article, .session-panel { flex: 1 1 220px; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 0.9rem; }
  .current-session .session-panel { justify-content: space-between; align-items: stretch; }
  .session-copy { display: grid; gap: 0.55rem; flex: 1 1 320px; }
  .session-copy strong, .event-main strong { margin: 0; }
  .session-metrics, .event-links { display: flex; flex-wrap: wrap; gap: 0.6rem; }
  .action-stack { display: grid; gap: 0.65rem; min-width: 220px; }
  .primary { background: #1d4ed8; color: #fff; border-color: #1d4ed8; }
  .primary.danger { background: #b91c1c; border-color: #b91c1c; }
  .secondary { color: #0f172a; }
  dl { display: grid; gap: 0.6rem; margin: 0.75rem 0 0; }
  dl div { display: flex; justify-content: space-between; gap: 1rem; }
  dt, dd { margin: 0; }
  .events-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.65rem; }
  .events-list li { border: 1px solid #e2e8f0; border-radius: 14px; padding: 0.8rem; background: #fff; }
  .events-list li.tone-critical { border-color: #fecaca; background: #fff7f7; }
  .events-list li.tone-warning { border-color: #fde68a; background: #fffbeb; }
  .events-list li.tone-info { border-color: #bfdbfe; background: #f8fbff; }
  .event-main { display: grid; gap: 0.35rem; flex: 1 1 auto; }
  .event-headline { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
  .events-list p { margin: 0.2rem 0 0; color: var(--text-secondary, #64748b); }
  .event-links a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  .event-meta { flex-direction: column; align-items: flex-end; color: var(--text-secondary, #64748b); font-size: 0.84rem; min-width: 140px; }
  .priority { display: inline-flex; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
  .priority.critical { background: #fee2e2; color: #b91c1c; }
  .priority.warning { background: #fef3c7; color: #92400e; }
  .priority.info { background: #dbeafe; color: #1d4ed8; }
  .priority.neutral { background: #e5e7eb; color: #475569; }
</style>
