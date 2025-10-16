<script>
  export let searchTerm = '';
</script>

<div class="search-container">
  <input 
    type="text" 
    placeholder="Search by name..." 
    bind:value={searchTerm}
  />
</div>

<style>
  .search-container { margin-bottom: 1rem; }
  input { width: 100%; padding: 0.5rem; font-size: 1rem; }
</style>