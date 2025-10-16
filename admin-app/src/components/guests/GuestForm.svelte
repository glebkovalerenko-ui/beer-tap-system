<!-- src/components/guests/GuestForm.svelte -->

<script>
  import { createEventDispatcher } from 'svelte';
  
  // `guest` - это prop. Если он передан, мы в режиме редактирования.
  // Если он null, мы в режиме создания.
  export let guest = null; 
  export let isSaving = false;

  const dispatch = createEventDispatcher();

  // Инициализируем formData со всеми полями, которые ожидает `schemas.GuestCreate`
  let formData = {
    last_name: guest?.last_name || '',
    first_name: guest?.first_name || '',
    patronymic: guest?.patronymic || '',
    phone_number: guest?.phone_number || '',
    date_of_birth: guest?.date_of_birth || '1990-01-01',
    id_document: guest?.id_document || '',
  };

  function handleSubmit() {
    // Отправляем событие 'save' с данными формы родителю
    dispatch('save', formData);
  }
</script>

<form on:submit|preventDefault={handleSubmit}>
  <h3>{guest ? 'Edit Guest' : 'Create New Guest'}</h3>
  
  <!-- Раздел с персональными данными -->
  <fieldset>
    <legend>Personal Information</legend>
    <div class="form-row">
      <div class="form-group">
        <label for="last_name">Last Name</label>
        <input id="last_name" type="text" bind:value={formData.last_name} required disabled={isSaving}/>
      </div>
      <div class="form-group">
        <label for="first_name">First Name</label>
        <input id="first_name" type="text" bind:value={formData.first_name} required disabled={isSaving}/>
      </div>
    </div>
    <div class="form-group">
      <label for="patronymic">Patronymic (Optional)</label>
      <input id="patronymic" type="text" bind:value={formData.patronymic} disabled={isSaving}/>
    </div>
    <div class="form-group">
      <label for="date_of_birth">Date of Birth</label>
      <input id="date_of_birth" type="date" bind:value={formData.date_of_birth} required disabled={isSaving}/>
    </div>
  </fieldset>

  <!-- Раздел с контактной информацией и документами -->
  <fieldset>
    <legend>Contact & ID</legend>
    <div class="form-group">
      <label for="phone_number">Phone Number</label>
      <input id="phone_number" type="text" placeholder="+79211234567" bind:value={formData.phone_number} required disabled={isSaving}/>
    </div>
    <div class="form-group">
      <label for="id_document">ID Document</label>
      <input id="id_document" type="text" placeholder="e.g., Passport Series and Number" bind:value={formData.id_document} required disabled={isSaving}/>
    </div>
  </fieldset>

  <!-- Кнопки управления формой -->
  <div class="form-actions">
    <button type="button" class="btn-secondary" on:click={() => dispatch('cancel')} disabled={isSaving}>Cancel</button>
    <button type="submit" class="btn-primary" disabled={isSaving}>
      {#if isSaving}Saving...{:else}Save Guest{/if}
    </button>
  </div>
</form>

<style>
  h3 { margin-top: 0; }
  fieldset { border: 1px solid #eee; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; }
  legend { font-weight: bold; padding: 0 0.5rem; }
  .form-row { display: flex; gap: 1rem; }
  .form-group { flex: 1; margin-bottom: 1rem; }
  label { display: block; margin-bottom: 0.25rem; font-size: 0.9rem; color: #555; }
  input { width: 100%; padding: 0.5rem; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
  .form-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.5rem; }
  .btn-primary { background-color: #007bff; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
  .btn-primary:disabled { background-color: #a0cfff; cursor: not-allowed; }
  .btn-secondary { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
</style>