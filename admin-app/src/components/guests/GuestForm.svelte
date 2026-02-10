<!-- src/components/guests/GuestForm.svelte -->

<script>
  import { createEventDispatcher } from 'svelte';
  
  // `guest` - это prop. Если он передан, мы в режиме редактирования.
  // Если он null, мы в режиме создания.
  export let guest = null; 
  export let isSaving = false;

  const dispatch = createEventDispatcher();

  // Инициализируем formData со всеми полями, которые ожидает `schemas.GuestCreate`
  // Эта логика уже отлично работает и для создания, и для редактирования.
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
    // Родитель решит, создавать нового гостя или обновлять существующего.
    dispatch('save', formData);
  }
</script>

<form on:submit|preventDefault={handleSubmit}>
  <!-- +++ ИЗМЕНЕНИЕ: Заголовок теперь динамический +++ -->
  <h3>{guest ? 'Редактирование данных гостя' : 'Добавление нового гостя'}</h3>
  
  <!-- Раздел с персональными данными -->
  <fieldset>
    <legend>Персональная информация</legend>
    <div class="form-row">
      <div class="form-group">
        <label for="last_name">Фамилия</label>
        <input id="last_name" type="text" bind:value={formData.last_name} required disabled={isSaving}/>
      </div>
      <div class="form-group">
        <label for="first_name">Имя</label>
        <input id="first_name" type="text" bind:value={formData.first_name} required disabled={isSaving}/>
      </div>
    </div>
    <div class="form-group">
      <label for="patronymic">Отчество (опционально)</label>
      <input id="patronymic" type="text" bind:value={formData.patronymic} disabled={isSaving}/>
    </div>
    <div class="form-group">
      <label for="date_of_birth">Дата рождения</label>
      <input id="date_of_birth" type="date" bind:value={formData.date_of_birth} required disabled={isSaving}/>
    </div>
  </fieldset>

  <!-- Раздел с контактной информацией и документами -->
  <fieldset>
    <legend>Контакты и документы</legend>
    <div class="form-group">
      <label for="phone_number">Номер телефона</label>
      <input id="phone_number" type="text" placeholder="+79211234567" bind:value={formData.phone_number} required disabled={isSaving}/>
    </div>
    <div class="form-group">
      <label for="id_document">ID документа</label>
      <input id="id_document" type="text" placeholder="напр. Серия и номер паспорта" bind:value={formData.id_document} required disabled={isSaving}/>
    </div>
  </fieldset>

  <!-- Кнопки управления формой -->
  <div class="form-actions">
    <button type="button" class="btn-secondary" on:click={() => dispatch('cancel')} disabled={isSaving}>Отмена</button>
    <button type="submit" class="btn-primary" disabled={isSaving}>
      {#if isSaving}
        Сохранение...
      {:else}
        <!-- +++ ИЗМЕНЕНИЕ: Текст кнопки теперь тоже динамический +++ -->
        {guest ? 'Сохранить изменения' : 'Добавить гостя'}
      {/if}
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