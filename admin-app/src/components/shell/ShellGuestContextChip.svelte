<script>
  export let guestName = 'Гость не выбран';
  export let cardUid = null;
  export let isActive = null;

  $: shortUid = cardUid ? `****${cardUid.slice(-4)}` : 'без карты';
  $: statusLabel = isActive === null ? '—' : (isActive ? 'active' : 'blocked');
</script>

<div class="chip">
  <strong>{guestName}</strong>
  <span>{shortUid} · {statusLabel}</span>
</div>

<style>
  .chip {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 12px;
    border-radius: 12px;
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    min-width: 190px;
  }
  strong { font-size: 0.9rem; }
  span { font-size: 0.78rem; color: var(--text-secondary); }
</style>
