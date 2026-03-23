<script>
  import { createEventDispatcher } from 'svelte';

  export let title = '';
  export let description = '';
  export let labelledBy = '';
  export let describedBy = '';
  export let width = 'min(720px, 100vw)';
  export let mobileFullWidth = true;
  export let showHeader = true;

  const dispatch = createEventDispatcher();

  function closeDrawer() {
    dispatch('close');
  }

  function focusOnMount(node) {
    node.focus();
  }
</script>

<svelte:window on:keydown={(event) => (event.key === 'Escape' ? closeDrawer() : null)} />

<div
  class="side-drawer-backdrop"
  on:click={closeDrawer}
  on:keydown={(event) => (event.key === 'Escape' ? closeDrawer() : null)}
  role="presentation"
>
  <div
    class:mobile-full-width={mobileFullWidth}
    class="side-drawer"
    style={`--side-drawer-width: ${width};`}
    on:click|stopPropagation
    on:keydown|stopPropagation={() => {}}
    role="dialog"
    aria-modal="true"
    aria-labelledby={labelledBy || undefined}
    aria-describedby={describedBy || undefined}
    tabindex="-1"
    use:focusOnMount
  >
    {#if showHeader}
      <header class="side-drawer__header">
        <div class="side-drawer__header-copy">
          <slot name="header">
            {#if title || description}
              {#if title}
                <h2>{title}</h2>
              {/if}
              {#if description}
                <p>{description}</p>
              {/if}
            {/if}
          </slot>
        </div>

        <button class="side-drawer__close" type="button" aria-label="Закрыть drawer" on:click={closeDrawer}>✕</button>
      </header>
    {/if}

    <div class="side-drawer__body">
      <slot />
    </div>

    {#if $$slots.footer}
      <footer class="side-drawer__footer">
        <slot name="footer" />
      </footer>
    {/if}
  </div>
</div>

<style>
  .side-drawer-backdrop {
    position: fixed;
    inset: 0;
    z-index: 950;
    background: rgba(15, 23, 42, 0.24);
    display: flex;
    justify-content: flex-end;
    align-items: stretch;
    padding-left: clamp(1rem, 5vw, 4rem);
  }

  .side-drawer {
    --side-drawer-width: min(720px, 100vw);
    width: min(var(--side-drawer-width), calc(100vw - clamp(0rem, 3vw, 2rem)));
    height: 100vh;
    background: #f8fafc;
    box-shadow: -18px 0 48px rgba(15, 23, 42, 0.18);
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto;
    overflow: hidden;
    border-left: 1px solid rgba(148, 163, 184, 0.28);
  }

  .side-drawer__header,
  .side-drawer__footer {
    position: relative;
    z-index: 1;
    background: rgba(248, 250, 252, 0.97);
    backdrop-filter: blur(10px);
  }

  .side-drawer__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid #e2e8f0;
  }

  .side-drawer__header-copy {
    min-width: 0;
  }

  .side-drawer__header-copy :global(h2),
  .side-drawer__header-copy :global(p) {
    margin: 0;
  }

  .side-drawer__header-copy :global(p) {
    margin-top: 0.35rem;
    color: var(--text-secondary, #64748b);
  }

  .side-drawer__body {
    overflow-y: auto;
    min-height: 0;
    padding: 1rem 1.25rem 1.25rem;
  }

  .side-drawer__footer {
    border-top: 1px solid #e2e8f0;
    padding: 0.9rem 1.25rem;
  }

  .side-drawer__close {
    border-radius: 999px;
    border: 1px solid #cbd5e1;
    background: #fff;
    width: 2.25rem;
    height: 2.25rem;
    font-size: 1rem;
    line-height: 1;
    flex: 0 0 auto;
  }

  @media (max-width: 720px) {
    .side-drawer-backdrop {
      padding-left: 0;
    }

    .side-drawer,
    .side-drawer.mobile-full-width {
      width: 100vw;
      max-width: 100vw;
      border-left: none;
    }
  }
</style>
