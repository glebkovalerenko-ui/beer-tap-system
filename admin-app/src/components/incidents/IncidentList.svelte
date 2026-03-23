<script>
  // @ts-nocheck
  import { createEventDispatcher } from 'svelte';
  import { formatDateTimeRu } from '../../lib/formatters.js';
  import { INCIDENT_COPY } from '../../lib/operatorLabels.js';

  export let groupedItems = [];
  export let selectedIncidentId = null;
  export let actionCapabilities = {};
  export let readOnly = false;

  const dispatch = createEventDispatcher();

  function emit(name, item) {
    dispatch(name, { item, incidentId: item.incident_id });
  }

  function actionLabel(item) {
    if (item.status === 'new') return 'Взять в работу';
    if (item.status === 'in_progress') return 'Закрыть';
    return 'Закрыт';
  }
</script>

<div class="incident-list">
  {#if groupedItems.every((group) => group.items.length === 0)}
    <p class="empty">{INCIDENT_COPY.noIncidentsFiltered}</p>
  {:else}
    {#each groupedItems as group (group.key)}
      <section class="incident-group">
        <div class="group-head">
          <div>
            <h2>{group.label}</h2>
            <p>{group.items.length} шт.</p>
          </div>
        </div>

        {#if group.items.length === 0}
          <p class="empty small">{INCIDENT_COPY.noIncidentsColumn}</p>
        {:else}
          <div class="incident-cards">
            {#each group.items as item (item.incident_id)}
              <article class:selected={selectedIncidentId === item.incident_id} class="incident-card">
                <div class="card-head">
                  <div>
                    <div class="eyebrow">#{item.incident_id}</div>
                    <strong>{item.typeLabel}</strong>
                    <p>{item.summary}</p>
                  </div>
                  <div class={`priority ${item.priority}`}>
                    {item.priorityLabel}
                  </div>
                </div>

                <div class="card-meta">
                  <span><strong>Кран:</strong> {item.tapLabel}</span>
                  <span><strong>Создан:</strong> {formatDateTimeRu(item.created_at)}</span>
                  <span><strong>Ответственный:</strong> {item.accountability.ownerLabel}</span>
                  <span><strong>Источник:</strong> {item.sourceLabel}</span>
                </div>

                <div class="state-row">
                  <span class={`status-badge ${item.status}`}>{item.statusLabel}</span>
                  <span class={`ownership-badge ${item.accountability.ownerState}`}>{item.accountability.ownerBadge}</span>
                  {#if item.accountability.lastEscalatedAt}
                    <span class="signal-badge">Эскалация {formatDateTimeRu(item.accountability.lastEscalatedAt)}</span>
                  {/if}
                  {#if readOnly}
                    <span class="signal-badge warning">{INCIDENT_COPY.readOnly}</span>
                  {/if}
                </div>

                <div class="card-links">
                  <button class="link" on:click|stopPropagation={() => emit('select', item)}>{INCIDENT_COPY.openDetails}</button>
                  <button class="link" on:click|stopPropagation={() => emit('openTap', item)}>{INCIDENT_COPY.openTap}</button>
                  <button class="link" on:click|stopPropagation={() => emit('openSession', item)}>{INCIDENT_COPY.openSession}</button>
                  <button class="link" on:click|stopPropagation={() => emit('openSystem', item)}>{INCIDENT_COPY.openSystem}</button>
                </div>

                <div class="card-actions">
                  {#if actionCapabilities.claim}
                    <button
                      class="secondary"
                      disabled={readOnly || item.status === 'closed'}
                      on:click|stopPropagation={() => emit('claimIncident', item)}
                    >
                      {actionLabel(item)}
                    </button>
                  {/if}
                  {#if actionCapabilities.escalate}
                    <button
                      class="secondary warning"
                      disabled={readOnly}
                      on:click|stopPropagation={() => emit('escalateIncident', item)}
                    >Эскалировать</button>
                  {/if}
                  {#if actionCapabilities.note || actionCapabilities.close}
                    <button class="primary" on:click|stopPropagation={() => emit('openActionForm', item)}>{INCIDENT_COPY.actionForm}</button>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </section>
    {/each}
  {/if}
</div>

<style>
  .incident-list, .incident-group, .incident-cards { display: grid; gap: 1rem; }
  .group-head, .card-head, .card-meta, .card-links, .card-actions, .state-row { display: flex; gap: 0.75rem; }
  .group-head, .card-head { justify-content: space-between; }
  .group-head h2, .group-head p, .card-head p { margin: 0; }
  .incident-card { border: 1px solid #e2e8f0; border-radius: 18px; padding: 1rem; background: #fff; display: grid; gap: 0.9rem; cursor: pointer; }
  .incident-card.selected { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb inset; background: #f8fbff; }
  .card-head p, .eyebrow, .empty, .small { color: var(--text-secondary, #64748b); }
  .priority { align-self: flex-start; border-radius: 999px; padding: 0.35rem 0.7rem; font-weight: 700; }
  .priority.low { background: #e2e8f0; }
  .priority.medium { background: #dbeafe; color: #1d4ed8; }
  .priority.high { background: #fef3c7; color: #92400e; }
  .priority.critical { background: #fee2e2; color: #b91c1c; }
  .card-meta, .state-row { flex-wrap: wrap; color: var(--text-secondary, #64748b); font-size: 0.92rem; }
  .card-links, .card-actions { flex-wrap: wrap; }
  .card-links .link, .card-actions button { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; background: #fff; font: inherit; font-weight: 700; }
  .card-links .link { color: #1d4ed8; }
  .card-actions .primary { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }
  .card-actions .warning { color: #92400e; background: #fffbeb; border-color: #fcd34d; }
  .card-actions button:disabled { opacity: 0.55; cursor: not-allowed; }
  .status-badge, .ownership-badge, .signal-badge { border-radius: 999px; padding: 0.25rem 0.65rem; font-size: 0.84rem; font-weight: 700; }
  .status-badge.new { background: #eff6ff; color: #1d4ed8; }
  .status-badge.in_progress { background: #fff7ed; color: #c2410c; }
  .status-badge.closed { background: #ecfdf3; color: #166534; }
  .ownership-badge.unassigned { background: #f8fafc; color: #475569; }
  .ownership-badge.assigned { background: #eef2ff; color: #3730a3; }
  .signal-badge { background: #f8fafc; color: #475569; }
  .signal-badge.warning { background: #fff7ed; color: #9a3412; }
</style>
