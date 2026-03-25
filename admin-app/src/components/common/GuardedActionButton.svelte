<script>
  export let visible = true;
  export let disabled = false;
  export let reason = '';
  export let className = '';
  export let ariaLabel = '';
  export let type = 'button';
</script>

{#if visible}
  <button
    {type}
    class={className}
    disabled={disabled}
    title={disabled ? (reason || 'Действие недоступно') : ''}
    aria-label={ariaLabel}
    on:click
  >
    <slot />
  </button>
{/if}
