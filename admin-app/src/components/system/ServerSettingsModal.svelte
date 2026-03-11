<script>
  import Modal from '../common/Modal.svelte';
  import {
    initializeBackendBaseUrl,
    serverConfigStore,
    setServerBaseUrl,
    testServerConnection,
    validateApiBaseUrl,
  } from '../../lib/config.js';
  import { normalizeErrorMessage } from '../../lib/errorUtils';
  import { uiStore } from '../../stores/uiStore.js';

  export let buttonLabel = 'Настройки сервера';
  export let variant = 'default';
  export let showLauncher = true;
  /** @type {'button' | 'submit' | 'reset'} */
  export let launcherType = 'button';

  let isOpen = false;
  let draftUrl = '';
  let inlineError = '';
  let successMessage = '';
  let isSaving = false;
  let isTesting = false;

  export async function openModal() {
    await initializeBackendBaseUrl();
    draftUrl = $serverConfigStore.baseUrl;
    inlineError = '';
    successMessage = '';
    isOpen = true;
  }

  function closeModal() {
    isOpen = false;
    inlineError = '';
    successMessage = '';
  }

  /** @param {MouseEvent} event */
  async function handleLauncherClick(event) {
    event?.preventDefault();
    await openModal();
  }

  async function handleTestConnection() {
    inlineError = '';
    successMessage = '';
    isTesting = true;

    try {
      const normalized = validateApiBaseUrl(draftUrl);
      const result = await testServerConnection(normalized);
      successMessage = `Соединение установлено: ${result.checked_url} (HTTP ${result.status_code})`;
    } catch (error) {
      inlineError = normalizeErrorMessage(error, 'Не удалось проверить соединение с сервером.');
    } finally {
      isTesting = false;
    }
  }

  async function handleSave() {
    inlineError = '';
    successMessage = '';
    isSaving = true;

    try {
      const normalized = validateApiBaseUrl(draftUrl);
      const savedBaseUrl = await setServerBaseUrl(normalized);
      draftUrl = savedBaseUrl;
      successMessage = `Сохранено: ${savedBaseUrl}`;
      uiStore.notifySuccess('Адрес сервера сохранён.');
    } catch (error) {
      inlineError = normalizeErrorMessage(error, 'Не удалось сохранить адрес сервера.');
    } finally {
      isSaving = false;
    }
  }
</script>

{#if showLauncher}
  <button class={`launcher ${variant}`} type={launcherType} on:click={handleLauncherClick}>
    {buttonLabel}
  </button>
{/if}

{#if isOpen}
  <Modal on:close={closeModal}>
    <div slot="header">
      <h2>Настройки сервера</h2>
    </div>

    <div class="settings-layout">
      <label class="settings-field" for="server-base-url">
        <span>Адрес сервера</span>
        <input
          id="server-base-url"
          type="url"
          bind:value={draftUrl}
          placeholder="http://cybeer-hub:8000"
          spellcheck="false"
          autocomplete="off"
          disabled={isSaving || isTesting}
        />
      </label>

      <p class="current-url">
        <strong>Текущий адрес:</strong> {$serverConfigStore.baseUrl}
      </p>
      <p class="settings-note">
        Источник: {$serverConfigStore.source === 'runtime-config' ? 'настройка приложения Tauri' : 'параметры сборки или dev-среды'}.
      </p>
      <p class="settings-note">
        Даже если сохранить недоступный адрес, приложение всё равно откроется и позволит исправить настройку здесь.
      </p>

      {#if !$serverConfigStore.runtimeConfigAvailable}
        <p class="warning">
          Изменение адреса доступно только в настольном приложении Tauri. В web/dev используйте `VITE_API_BASE_URL`.
        </p>
      {/if}

      {#if inlineError}
        <p class="error">{inlineError}</p>
      {/if}

      {#if successMessage}
        <p class="success">{successMessage}</p>
      {/if}
    </div>

    <div slot="footer" class="actions">
      <button class="secondary" on:click={closeModal}>Закрыть</button>
      <button
        class="secondary"
        on:click={handleTestConnection}
        disabled={!$serverConfigStore.runtimeConfigAvailable || isSaving || isTesting}
      >
        {#if isTesting}Проверка...{:else}Проверить соединение{/if}
      </button>
      <button
        on:click={handleSave}
        disabled={!$serverConfigStore.runtimeConfigAvailable || isSaving || isTesting}
      >
        {#if isSaving}Сохранение...{:else}Сохранить{/if}
      </button>
    </div>
  </Modal>
{/if}

<style>
  .settings-layout {
    display: grid;
    gap: 0.9rem;
  }

  .launcher.ghost,
  .secondary,
  .launcher.secondary {
    background: #edf2fb;
    color: #23416b;
  }

  .settings-field {
    display: grid;
    gap: 0.35rem;
    font-weight: 600;
  }

  .current-url,
  .settings-note,
  .warning,
  .error,
  .success {
    margin: 0;
  }

  .settings-note {
    color: var(--text-secondary);
  }

  .warning {
    color: #8a5a00;
  }

  .error {
    color: #c61f35;
  }

  .success {
    color: #1d7a46;
  }

  .actions {
    display: flex;
    gap: 0.75rem;
  }
</style>
