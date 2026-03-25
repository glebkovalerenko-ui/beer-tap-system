<script>
  export let label = 'Данные';
  export let lastFetchedAt = null;
  export let staleAfterMs = 10000;
  export let mode = 'online';
  export let transport = 'websocket';
  export let reason = null;

  function ageLabel(value) {
    if (!value) return 'нет снимка';
    const ageMs = Math.max(0, Date.now() - Number(value));
    if (ageMs < 1000) return 'только что';
    if (ageMs < 60000) return `${Math.round(ageMs / 1000)} с назад`;
    return `${Math.round(ageMs / 60000)} мин назад`;
  }

  $: isStale = Boolean(lastFetchedAt) && (Date.now() - Number(lastFetchedAt)) > staleAfterMs;
  $: tone = mode === 'offline'
    ? 'critical'
    : mode !== 'online' || transport !== 'websocket' || isStale
      ? 'warning'
      : 'neutral';
  $: modeLabel = mode === 'offline'
    ? 'offline'
    : mode === 'backend_degraded'
      ? 'degraded'
      : mode === 'controller_only'
        ? 'controller only'
        : transport === 'websocket'
          ? 'live'
          : transport === 'short_polling'
            ? 'polling'
            : transport === 'reduced_polling'
              ? 'reduced'
              : 'snapshot';
  $: title = reason || `${label}: ${ageLabel(lastFetchedAt)}`;
</script>

<span class="freshness-chip" data-tone={tone} title={title}>
  <strong>{label}</strong>
  <span>{ageLabel(lastFetchedAt)}</span>
  <small>{modeLabel}</small>
</span>

<style>
  .freshness-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    border-radius: 999px;
    padding: 0.38rem 0.75rem;
    border: 1px solid var(--state-neutral-border, #cbd5e1);
    background: var(--state-neutral-bg, #eff6ff);
    color: var(--state-neutral-text, #1e3a8a);
    font-size: 0.8rem;
  }

  .freshness-chip small {
    color: inherit;
    opacity: 0.8;
  }

  .freshness-chip[data-tone='warning'] {
    border-color: var(--state-warning-border, #fcd34d);
    background: var(--state-warning-bg, #fff7ed);
    color: var(--state-warning-text, #9a3412);
  }

  .freshness-chip[data-tone='critical'] {
    border-color: var(--state-critical-border, #fca5a5);
    background: var(--state-critical-bg, #fff1f2);
    color: var(--state-critical-text, #9f1239);
  }
</style>
