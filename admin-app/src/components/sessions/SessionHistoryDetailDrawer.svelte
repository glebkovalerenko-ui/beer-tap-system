<script>
  import { SESSION_COPY } from '../../lib/operatorLabels.js';

  export let detail;
  export let detailNarrativeGroups;
  export let detailDisplayContext;
  export let detailOperatorActions;
  export let detailWhatHappened = [];
  export let narrativeKindLabels;
  export let formatMaybeDate;
  export let onCloseDetail = () => {};
</script>

<aside class="ui-card drawer" class:drawer-open={detail}>
  {#if detail}
    <div class="drawer-head">
      <div>
        <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
        <h2>{detail.summary.guest_full_name}</h2>
        <p>{detail.summary.card_uid || 'Без карты'} · {detail.summary.operator_status}</p>
      </div>
      <button on:click={onCloseDetail}>✕</button>
    </div>

    <section class="summary-section">
      <h3>Что произошло</h3>
      {#each detailWhatHappened as sentence}
        <p>{sentence}</p>
      {/each}
    </section>

    <section class="stats-grid">
      {#each detailNarrativeGroups.lifecycleCards as card}
        <article>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <small>{card.note}</small>
        </article>
      {/each}
    </section>

    <section class="timeline-section">
      <h3>{SESSION_COPY.lifecycleSummary}</h3>
      <dl>
        <div><dt>Открытие</dt><dd>{formatMaybeDate(detail.summary.lifecycle.opened_at)}</dd></div>
        <div><dt>Авторизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_authorized_at)}</dd></div>
        <div><dt>Старт налива</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
        <div><dt>Последний налив завершён</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
        <div><dt>Последняя синхронизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_sync_at)}</dd></div>
        <div><dt>Закрытие / прерывание</dt><dd>{formatMaybeDate(detail.summary.lifecycle.closed_at)}</dd></div>
      </dl>
    </section>

    <section class="timeline-section">
      <h3>Ход сессии</h3>
      <ul class="timeline">
        {#each detailNarrativeGroups.timeline as event}
          <li>
            <div class="time">{formatMaybeDate(event.timestamp)}</div>
            <div>
              <strong>{event.title}</strong>
              <p>{event.description}</p>
              {#if event.status}<small>{narrativeKindLabels[event.kind] || event.kind} · {event.status}</small>{/if}
            </div>
          </li>
        {/each}
      </ul>
    </section>

    <section class="timeline-section">
      <h3>{SESSION_COPY.operatorContext}</h3>
      {#if detailNarrativeGroups.operatorObservations.length}
        <ul class="timeline compact">
          {#each detailNarrativeGroups.operatorObservations as observation}
            <li><div class="time">Контекст</div><div><strong>{observation.title}</strong><p>{observation.description}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Дополнительных операторских наблюдений система не передала.</p>
      {/if}
    </section>

    <section class="timeline-section display-context-section">
      <h3>{detailDisplayContext.title}</h3>
      {#if detailDisplayContext.tapLabel}
        <p class="muted">Контекст для {detailDisplayContext.tapLabel}.</p>
      {/if}
      {#if detailDisplayContext.available}
        <dl class="display-context-grid">
          {#each detailDisplayContext.fields as field}
            <div><dt>{field.label}</dt><dd>{field.value}</dd></div>
          {/each}
        </dl>
        <div class="summary-section nested-summary">
          <strong>Важные override-поля</strong>
          {#if detailDisplayContext.overrides.length}
            <ul class="override-list">
              {#each detailDisplayContext.overrides as override}
                <li>{override}</li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Override-поля не влияли на guest-facing поведение.</p>
          {/if}
          {#if detailDisplayContext.note}
            <p class="muted">{detailDisplayContext.note}</p>
          {/if}
          {#if detailDisplayContext.incidentLink}
            <p>{detailDisplayContext.incidentLink}</p>
          {/if}
        </div>
      {:else}
        <p class="muted">{detailDisplayContext.placeholder}</p>
        {#if detailDisplayContext.incidentLink}
          <p>{detailDisplayContext.incidentLink}</p>
        {/if}
      {/if}
    </section>

    <section class="timeline-section">
      <h3>{SESSION_COPY.operatorActions}</h3>
      {#if detailOperatorActions.length}
        <ul class="timeline compact">
          {#each detailOperatorActions as action}
            <li><div class="time">{formatMaybeDate(action.timestamp)}</div><div><strong>{action.label}</strong><p>{action.details || 'Без дополнительного комментария'}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Явных вмешательств оператора не было.</p>
      {/if}
    </section>
  {:else}
    <div class="empty-drawer">
      <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
      <h2>Выберите сессию</h2>
      <p>{SESSION_COPY.emptyDetailsText}</p>
    </div>
  {/if}
</aside>
