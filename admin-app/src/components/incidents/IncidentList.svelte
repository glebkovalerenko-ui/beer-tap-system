<script>
  // @ts-nocheck
  import { createEventDispatcher } from 'svelte';
  import { formatDateTimeRu } from '../../lib/formatters.js';

  export let groupedItems = [];
  export let selectedIncidentId = null;

  const dispatch = createEventDispatcher();

  function emit(name, item) {
    dispatch(name, { item, incidentId: item.incident_id });
  }
</script>

<div class="incident-list">
  {#if groupedItems.every((group) => group.items.length === 0)}
    <p class="empty">Нет инцидентов по выбранным фильтрам.</p>
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
          <p class="empty small">В этой колонке сейчас пусто.</p>
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
                  <span><strong>Оператор:</strong> {item.operator || 'Не назначен'}</span>
                  <span><strong>Источник:</strong> {item.sourceLabel}</span>
                </div>

                <div class="card-links">
                  <button class="link" on:click|stopPropagation={() => emit('select', item)}>Открыть детали</button>
                  <button class="link" on:click|stopPropagation={() => emit('openTap', item)}>Открыть кран</button>
                  <button class="link" on:click|stopPropagation={() => emit('openSession', item)}>Открыть сессию</button>
                  <button class="link" on:click|stopPropagation={() => emit('openSystem', item)}>System</button>
                </div>

                <div class="card-actions">
                  <button class="secondary" on:click|stopPropagation={() => emit('closeIncident', item)}>Закрыть</button>
                  <button class="secondary warning" on:click|stopPropagation={() => emit('escalateIncident', item)}>Эскалировать</button>
                  <button class="primary" on:click|stopPropagation={() => emit('addNote', item)}>Добавить заметку</button>
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
  .group-head, .card-head, .card-meta, .card-links, .card-actions { display: flex; gap: 0.75rem; }
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
  .card-meta { flex-wrap: wrap; color: var(--text-secondary, #64748b); font-size: 0.92rem; }
  .card-links, .card-actions { flex-wrap: wrap; }
  .card-links .link, .card-actions button { border: 1px solid #cbd5e1; border-radius: 10px; padding: 0.65rem 0.8rem; background: #fff; font: inherit; font-weight: 700; }
  .card-links .link { color: #1d4ed8; }
  .card-actions .primary { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }
  .card-actions .warning { color: #92400e; background: #fffbeb; border-color: #fcd34d; }
</style>
