<script>
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

  function nextStep(item) {
    if (item.canonical_visit_status === 'blocked') return 'Проверить блокировку и карту';
    if (item.canonical_visit_status === 'needs_attention') return 'Разобрать инцидент или синхронизацию';
    if (item.canonical_visit_status === 'awaiting_action') return 'Нужно действие по визиту';
    if (item.canonical_visit_status === 'pouring_now') return 'Следить за наливом';
    if (item.isActive) return 'Открыть визит';
    return 'Проверить итог визита';
  }

  function tapSummary(item) {
    return item.taps?.length ? `краны: ${item.taps.join(', ')}` : 'кран не выбран';
  }
</script>

<section class="list-stack">
  <section class="ui-card list-panel pinned-panel">
    <div class="list-head">
      <div>
        <h3>Нужно сейчас</h3>
        <p>Открытые визиты и те, где оператору важно быстро увидеть гостя и следующее действие.</p>
      </div>
      <span class="counter">{pinnedActiveItems.length}</span>
    </div>

    {#if pinnedActiveItems.length === 0}
      <p class="muted">Активных визитов по текущим фильтрам нет.</p>
    {:else}
      <div class="session-list compact-list">
        {#each pinnedActiveItems as item}
          <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item pinned" on:click={() => onOpenDetail(item)}>
            <div class="row top">
              <strong>{item.guest_full_name}</strong>
              <span class="state active">{item.operator_status}</span>
            </div>
            <div class="row meta-grid">
              <span>{item.card_uid || 'без карты'}</span>
              <span>{tapSummary(item)}</span>
            </div>
            <div class="row meta-grid">
              <span>Открыт: {formatMaybeDate(item.opened_at)}</span>
              <span>Последнее действие: {formatMaybeDate(item.last_event_at)}</span>
            </div>
            <div class="row">
              <span class="completion-pill">Следующий шаг: {nextStep(item)}</span>
            </div>
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
        <h3>{filters.activeOnly ? 'Активные визиты по фильтру' : 'Журнал визитов'}</h3>
        <p>Каждая строка отвечает на четыре вопроса: кто, в каком статусе, на каком кране и что делать дальше.</p>
      </div>
      <span class="counter">{journalItems.length}</span>
    </div>

    {#if journalItems.length === 0}
      <p class="muted">По выбранным фильтрам визиты не найдены.</p>
    {:else}
      <div class="session-list">
        {#each journalItems as item}
          <button class:selected={String(item.visit_id) === String(selectedVisitId)} class="session-item" on:click={() => onOpenDetail(item)}>
            <div class="row top">
              <strong>{item.guest_full_name}</strong>
              <span class:active={item.isActive} class="state">{item.operator_status}</span>
            </div>
            <div class="row meta-grid">
              <span>{item.card_uid || 'без карты'}</span>
              <span>{tapSummary(item)}</span>
            </div>
            <div class="row meta-grid">
              <span>Открыт: {formatMaybeDate(item.opened_at)}</span>
              <span>Последнее действие: {formatMaybeDate(item.last_event_at)}</span>
            </div>
            <div class="row">
              <span class="completion-pill">{describeCompletionSourceDetails(item)}</span>
              <span class="completion-pill">Следующий шаг: {nextStep(item)}</span>
            </div>
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
