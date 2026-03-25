<script>
  import { SESSION_COPY } from '../../lib/operatorLabels.js';
  import { buildSessionBadges } from '../../lib/operator/sessionBadgeModel.js';

  export let pinnedActiveItems = [];
  export let journalItems = [];
  export let selectedVisitId = '';
  export let filters;
  export let syncLabels;
  export let formatMaybeDate;
  export let describeCompletionSourceDetails;
  export let isZeroVolumeAbort;
  export let onOpenDetail = () => {};
</script>

<section class="list-stack">
  <section class="ui-card list-panel pinned-panel">
    <div class="list-head">
      <div>
        <h3>Активные сейчас</h3>
        <p>Закреплённый блок помогает сразу видеть, что ещё не завершено.</p>
      </div>
      <span class="counter">{pinnedActiveItems.length}</span>
    </div>

    {#if pinnedActiveItems.length === 0}
      <p class="muted">{SESSION_COPY.emptyActive}</p>
    {:else}
      <div class="session-list compact-list">
        {#each pinnedActiveItems as item}
          <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item pinned" on:click={() => onOpenDetail(item)}>
            <div class="row top"><strong>{item.guest_full_name}</strong><span class="state active">Активна</span></div>
            <div class="row"><span>Карта: {item.card_uid || '—'}</span><span>Кран: {item.taps?.length ? item.taps.join(', ') : '—'}</span></div>
            <div class="row"><span>Открыта: {formatMaybeDate(item.opened_at)}</span><span>Последнее событие: {formatMaybeDate(item.last_event_at)}</span></div>
            <div class="chips">
              {#each buildSessionBadges(item, { syncLabels, isZeroVolumeAbort }) as badge (badge.key)}
                <span data-tone={badge.tone}>{badge.label}</span>
              {/each}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </section>

  <section class="ui-card list-panel">
    <div class="list-head">
      <div>
        <h3>{filters.activeOnly ? 'Отфильтрованные активные сессии' : 'История и завершённые сессии'}</h3>
        <p>{SESSION_COPY.openDetailsHint}</p>
      </div>
      <span class="counter">{journalItems.length}</span>
    </div>

    {#if journalItems.length === 0}
      <p class="muted">{SESSION_COPY.emptyList}</p>
    {:else}
      <div class="session-list">
        {#each journalItems as item}
          <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item" on:click={() => onOpenDetail(item)}>
            <div class="row top">
              <strong>{item.guest_full_name}</strong>
              <span class:active={item.isActive} class="state">{item.operator_status}</span>
            </div>
            <div class="row meta-grid"><span>Карта: {item.card_uid || '—'}</span><span>Кран: {item.taps?.length ? item.taps.join(', ') : '—'}</span></div>
            <div class="row"><span>Открыта: {formatMaybeDate(item.opened_at)}</span><span>Последнее событие: {formatMaybeDate(item.last_event_at)}</span></div>
            <div class="row"><span class="completion-pill">Причина завершения: {describeCompletionSourceDetails(item)}</span></div>
            <div class="chips">
              {#each buildSessionBadges(item, { syncLabels, isZeroVolumeAbort }) as badge (badge.key)}
                <span data-tone={badge.tone}>{badge.label}</span>
              {/each}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </section>
</section>
