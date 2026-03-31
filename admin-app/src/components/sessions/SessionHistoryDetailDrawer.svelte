<script>
  export let detail;
  export let detailNarrativeGroups;
  export let detailDisplayContext;
  export let detailOperatorActions;
  export let detailWhatHappened = [];
  export let narrativeKindLabels;
  export let formatMaybeDate;
  export let syncLabels = {};
  export let actionLoading = false;
  export let actionError = null;
  export let readOnlyReason = '';
  export let getActionDisabledReason = () => '';
  export let onCloseSession = () => {};
  export let onForceUnlock = () => {};
  export let onReconcileSession = () => {};
  export let onMarkLostCard = () => {};
  export let onOpenVisitWorkspace = () => {};
  export let onOpenGuest = () => {};
  export let onOpenTap = () => {};
  export let onOpenPours = () => {};
  export let onCloseDetail = () => {};
  $: isBlockedLost = detail?.summary?.operational_status === 'active_blocked_lost_card';

  $: syncSummaryItems = detail ? [
    {
      key: 'sync-state',
      label: 'Синхронизация',
      value: syncLabels[detail.summary.sync_state] || detail.summary.sync_state || 'Нет данных',
      note: detail.summary.has_unsynced ? 'Есть данные, ожидающие синхронизацию.' : 'Дополнительная синхронизация не требуется.',
    },
    {
      key: 'last-sync',
      label: 'Последняя синхронизация',
      value: formatMaybeDate(detail.summary.lifecycle.last_sync_at),
      note: null,
    },
    {
      key: 'incident-count',
      label: 'Инциденты',
      value: detail.summary.has_incident ? `${detail.summary.incident_count || 1}` : 'Нет',
      note: detail.summary.has_incident ? 'Перед закрытием сверьте связанный инцидент и состояние крана.' : null,
    },
  ] : [];

  $: actionButtons = detail ? (isBlockedLost
    ? []
    : [
      { key: 'close', label: 'Закрыть визит', policy: detail.safe_actions?.close, handler: onCloseSession, tone: 'danger' },
      { key: 'force_unlock', label: 'Снять блокировку', policy: detail.safe_actions?.force_unlock, handler: onForceUnlock, tone: 'neutral' },
      { key: 'reconcile', label: 'Ручная сверка', policy: detail.safe_actions?.reconcile, handler: onReconcileSession, tone: 'neutral' },
      { key: 'mark_lost_card', label: 'Отметить карту потерянной', policy: detail.safe_actions?.mark_lost_card, handler: onMarkLostCard, tone: 'danger' },
    ]) : [];
</script>

<aside class="ui-card drawer" class:drawer-open={detail}>
  {#if detail}
    <div class="drawer-head">
      <div>
        <div class="eyebrow">Детали визита</div>
        <h2>{detail.summary.guest_full_name}</h2>
        <p>{detail.summary.card_uid || 'Без карты'} · {detail.summary.operator_status}</p>
      </div>
      <button on:click={onCloseDetail}>Закрыть</button>
    </div>

    <section class="summary-section actions-summary">
      <div class="section-inline-head">
        <h3>Быстрые действия</h3>
        {#if readOnlyReason}
          <span class="muted">{readOnlyReason}</span>
        {/if}
      </div>
      {#if actionButtons.length > 0}
        <div class="action-grid">
          {#each actionButtons as action}
            <button
              class="action-button"
              data-tone={action.tone}
              disabled={Boolean(getActionDisabledReason(action.policy)) || actionLoading}
              title={getActionDisabledReason(action.policy)}
              on:click={action.handler}
            >
              {action.label}
            </button>
          {/each}
        </div>
      {:else if isBlockedLost}
        <p class="muted recovery-hint">Для blocked-lost визита доступны только перевыпуск или service-close в разделе «Визиты».</p>
      {/if}
      {#if actionError}
        <p class="action-error">{actionError}</p>
      {/if}
    </section>

    <section class="summary-section route-shortcuts">
      <div class="section-inline-head">
        <h3>Быстрые переходы</h3>
      </div>
      <div class="shortcut-grid">
        <button class="action-button" type="button" on:click={onOpenVisitWorkspace} disabled={!detail.summary.visit_id}>Открыть визит</button>
        <button class="action-button" type="button" on:click={onOpenGuest} disabled={!detail.summary.guest_id && !detail.summary.card_uid}>Открыть гостя</button>
        <button class="action-button" type="button" on:click={onOpenTap} disabled={!detail.summary.primary_tap_id}>Открыть кран</button>
        <button class="action-button" type="button" on:click={onOpenPours} disabled={!detail.summary.visit_id}>Открыть наливы визита</button>
      </div>
    </section>

    <section class="summary-section">
      <h3>Что происходит</h3>
      {#each detailWhatHappened as sentence}
        <p>{sentence}</p>
      {/each}
    </section>

    <section class="timeline-section">
      <h3>Состояние визита</h3>
      <div class="stats-grid">
        {#each detailNarrativeGroups.lifecycleCards as card}
          <article>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <small>{card.note}</small>
          </article>
        {/each}
      </div>
      <dl>
        <div><dt>Открыт</dt><dd>{formatMaybeDate(detail.summary.lifecycle.opened_at)}</dd></div>
        <div><dt>Авторизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_authorized_at)}</dd></div>
        <div><dt>Первый налив</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
        <div><dt>Последний налив</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
        <div><dt>Последняя синхронизация</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_sync_at)}</dd></div>
        <div><dt>Закрыт</dt><dd>{formatMaybeDate(detail.summary.lifecycle.closed_at)}</dd></div>
      </dl>
    </section>

    <section class="timeline-section">
      <h3>Наливы и события визита</h3>
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
      <h3>Контроль и синхронизация</h3>
      <div class="stats-grid">
        {#each syncSummaryItems as item}
          <article>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            {#if item.note}
              <small>{item.note}</small>
            {/if}
          </article>
        {/each}
      </div>
      {#if detailNarrativeGroups.operatorObservations.length}
        <ul class="timeline compact">
          {#each detailNarrativeGroups.operatorObservations as observation}
            <li><div class="time">Контекст</div><div><strong>{observation.title}</strong><p>{observation.description}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Дополнительных предупреждений по визиту система не вернула.</p>
      {/if}
    </section>

    <section class="timeline-section">
      <h3>Действия оператора</h3>
      {#if detailOperatorActions.length}
        <ul class="timeline compact">
          {#each detailOperatorActions as action}
            <li><div class="time">{formatMaybeDate(action.timestamp)}</div><div><strong>{action.label}</strong><p>{action.details || 'Без дополнительного комментария'}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">Явных ручных действий по этому визиту не зафиксировано.</p>
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
          <strong>Изменения экрана</strong>
          {#if detailDisplayContext.overrides.length}
            <ul class="override-list">
              {#each detailDisplayContext.overrides as override}
                <li>{override}</li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Экран крана не менялся вручную в этом визите.</p>
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
  {:else}
    <div class="empty-drawer">
      <div class="eyebrow">Детали визита</div>
      <h2>Выберите визит</h2>
      <p>Откройте любую строку в активном блоке или журнале, чтобы увидеть гостя, наливы, проблемы и доступные действия.</p>
    </div>
  {/if}
</aside>

<style>
  .actions-summary,
  .action-grid,
  .shortcut-grid { display: grid; gap: 0.75rem; }
  .section-inline-head { display: flex; justify-content: space-between; gap: 0.75rem; align-items: start; }
  .section-inline-head h3,
  .action-error { margin: 0; }
  .action-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .shortcut-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .action-button {
    border-radius: 12px;
    border: 1px solid #cbd5e1;
    background: #fff;
    padding: 0.75rem 0.85rem;
    font-weight: 700;
  }
  .action-button[data-tone='danger'] {
    border-color: var(--state-critical-border, #fca5a5);
    color: var(--state-critical-text, #9f1239);
  }
  .action-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .action-error {
    color: var(--state-critical-text, #9f1239);
  }
  .recovery-hint {
    margin: 0;
  }
  @media (max-width: 820px) {
    .action-grid,
    .shortcut-grid { grid-template-columns: 1fr; }
  }
</style>
