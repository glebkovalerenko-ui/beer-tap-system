<script>
  import { SESSION_COPY } from '../../lib/operatorLabels.js';

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
  export let onCloseDetail = () => {};

  $: syncSummaryItems = detail ? [
    {
      key: 'sync-state',
      label: 'Sync status',
      value: syncLabels[detail.summary.sync_state] || detail.summary.sync_state || 'No data',
      note: detail.summary.has_unsynced ? 'There is data waiting for sync.' : 'This session does not need extra sync.',
    },
    {
      key: 'last-sync',
      label: 'Last sync',
      value: formatMaybeDate(detail.summary.lifecycle.last_sync_at),
      note: null,
    },
    {
      key: 'incident-count',
      label: 'Session incidents',
      value: detail.summary.has_incident ? `${detail.summary.incident_count || 1}` : 'No',
      note: detail.summary.has_incident ? 'Check related incident context before closing the case.' : null,
    },
  ] : [];

  $: actionButtons = detail ? [
    { key: 'close', label: 'Close', policy: detail.safe_actions?.close, handler: onCloseSession, tone: 'danger' },
    { key: 'force_unlock', label: 'Force unlock', policy: detail.safe_actions?.force_unlock, handler: onForceUnlock, tone: 'neutral' },
    { key: 'reconcile', label: 'Reconcile', policy: detail.safe_actions?.reconcile, handler: onReconcileSession, tone: 'neutral' },
    { key: 'mark_lost_card', label: 'Mark lost card', policy: detail.safe_actions?.mark_lost_card, handler: onMarkLostCard, tone: 'danger' },
  ] : [];
</script>

<aside class="ui-card drawer" class:drawer-open={detail}>
  {#if detail}
    <div class="drawer-head">
      <div>
        <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
        <h2>{detail.summary.guest_full_name}</h2>
        <p>{detail.summary.card_uid || 'No card'} - {detail.summary.operator_status}</p>
      </div>
      <button on:click={onCloseDetail}>вњ•</button>
    </div>

    <section class="summary-section actions-summary">
      <div class="section-inline-head">
        <h3>Safe actions</h3>
        {#if readOnlyReason}
          <span class="muted">{readOnlyReason}</span>
        {/if}
      </div>
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
      {#if actionError}
        <p class="action-error">{actionError}</p>
      {/if}
    </section>

    <section class="summary-section">
      <h3>What happened</h3>
      {#each detailWhatHappened as sentence}
        <p>{sentence}</p>
      {/each}
    </section>

    <section class="timeline-section">
      <h3>{SESSION_COPY.lifecycleSummary}</h3>
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
        <div><dt>Opened</dt><dd>{formatMaybeDate(detail.summary.lifecycle.opened_at)}</dd></div>
        <div><dt>Authorized</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_authorized_at)}</dd></div>
        <div><dt>Pour started</dt><dd>{formatMaybeDate(detail.summary.lifecycle.first_pour_started_at)}</dd></div>
        <div><dt>Last pour ended</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_pour_ended_at)}</dd></div>
        <div><dt>Last sync</dt><dd>{formatMaybeDate(detail.summary.lifecycle.last_sync_at)}</dd></div>
        <div><dt>Closed / aborted</dt><dd>{formatMaybeDate(detail.summary.lifecycle.closed_at)}</dd></div>
      </dl>
    </section>

    <section class="timeline-section">
      <h3>Session timeline</h3>
      <ul class="timeline">
        {#each detailNarrativeGroups.timeline as event}
          <li>
            <div class="time">{formatMaybeDate(event.timestamp)}</div>
            <div>
              <strong>{event.title}</strong>
              <p>{event.description}</p>
              {#if event.status}<small>{narrativeKindLabels[event.kind] || event.kind} - {event.status}</small>{/if}
            </div>
          </li>
        {/each}
      </ul>
    </section>

    <section class="timeline-section">
      <h3>Sync and control</h3>
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
            <li><div class="time">Context</div><div><strong>{observation.title}</strong><p>{observation.description}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">No extra sync or operator-control warnings were returned by the system.</p>
      {/if}
    </section>

    <section class="timeline-section">
      <h3>{SESSION_COPY.operatorActions}</h3>
      {#if detailOperatorActions.length}
        <ul class="timeline compact">
          {#each detailOperatorActions as action}
            <li><div class="time">{formatMaybeDate(action.timestamp)}</div><div><strong>{action.label}</strong><p>{action.details || 'No extra comment'}</p></div></li>
          {/each}
        </ul>
      {:else}
        <p class="muted">No explicit operator interventions were recorded.</p>
      {/if}
    </section>

    <section class="timeline-section display-context-section">
      <h3>{detailDisplayContext.title}</h3>
      {#if detailDisplayContext.tapLabel}
        <p class="muted">Context for {detailDisplayContext.tapLabel}.</p>
      {/if}
      {#if detailDisplayContext.available}
        <dl class="display-context-grid">
          {#each detailDisplayContext.fields as field}
            <div><dt>{field.label}</dt><dd>{field.value}</dd></div>
          {/each}
        </dl>
        <div class="summary-section nested-summary">
          <strong>Important override fields</strong>
          {#if detailDisplayContext.overrides.length}
            <ul class="override-list">
              {#each detailDisplayContext.overrides as override}
                <li>{override}</li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Override fields did not affect what the guest saw on the display.</p>
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
      <div class="eyebrow">{SESSION_COPY.detailsPanel}</div>
      <h2>Select a session</h2>
      <p>{SESSION_COPY.emptyDetailsText}</p>
    </div>
  {/if}
</aside>

<style>
  .actions-summary,
  .action-grid { display: grid; gap: 0.75rem; }
  .section-inline-head { display: flex; justify-content: space-between; gap: 0.75rem; align-items: start; }
  .section-inline-head h3,
  .action-error { margin: 0; }
  .action-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
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
</style>
