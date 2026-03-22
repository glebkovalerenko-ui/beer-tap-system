<!-- src/components/pours/PourFeed.svelte -->
<script>
  import EventFeed from './EventFeed.svelte';

  export let items = [];
  export let title = 'Живая лента наливов';
  export let emptyMessage = 'Нет недавних наливов для отображения.';
  export let onOpenTap = () => {};
  export let onOpenSession = () => {};
  export let onDismiss = () => {};
</script>

<EventFeed
  {items}
  {title}
  {emptyMessage}
  {onOpenTap}
  {onOpenSession}
  {onDismiss}
/>
