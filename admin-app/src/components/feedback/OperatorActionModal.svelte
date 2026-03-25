<script>
  import Modal from '../common/Modal.svelte';
  import { operatorActionStore } from '../../stores/operatorActionStore.js';
  import { normalizeOperatorActionValues } from '../../lib/operator/actionDialogModel.js';

  let activeRequestId = null;
  let values = {};
  let errors = {};

  function syncRequest(request) {
    activeRequestId = request?.id ?? null;
    values = { ...(request?.initialValues || {}) };
    errors = {};
  }

  function submit(request) {
    const nextErrors = request?.validate ? request.validate(values) : {};
    errors = nextErrors || {};
    if (Object.keys(errors).length > 0) {
      return;
    }
    operatorActionStore.resolve({
      values: normalizeOperatorActionValues(values),
    });
  }

  function close() {
    operatorActionStore.cancel();
  }

  $: if ($operatorActionStore.request && $operatorActionStore.request.id !== activeRequestId) {
    syncRequest($operatorActionStore.request);
  }
</script>

{#if $operatorActionStore.request}
  <Modal on:close={close}>
    <div slot="header">
      <h2>{$operatorActionStore.request.title}</h2>
      {#if $operatorActionStore.request.description}
        <p class="subtitle">{$operatorActionStore.request.description}</p>
      {/if}
    </div>

    <div class="action-modal" data-mode={$operatorActionStore.request.mode}>
      {#if $operatorActionStore.request.blockedReason}
        <div class="blocked-banner">{$operatorActionStore.request.blockedReason}</div>
      {/if}

      {#if $operatorActionStore.request.fields?.length > 0}
        <div class="fields">
          {#each $operatorActionStore.request.fields as field (field.name)}
            <label>
              <span>{field.label}</span>

              {#if field.type === 'textarea'}
                <textarea
                  rows={field.rows || 4}
                  bind:value={values[field.name]}
                  placeholder={field.placeholder || ''}
                ></textarea>
              {:else if field.type === 'select'}
                <select bind:value={values[field.name]}>
                  <option value="">Select an option</option>
                  {#each field.options || [] as option (option.value)}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
                {#if values[field.name]}
                  {#each field.options || [] as option (option.value)}
                    {#if option.value === values[field.name] && option.description}
                      <small>{option.description}</small>
                    {/if}
                  {/each}
                {/if}
              {:else}
                <input
                  type={field.type || 'text'}
                  bind:value={values[field.name]}
                  placeholder={field.placeholder || ''}
                  min={field.min}
                  step={field.step}
                  inputmode={field.inputMode || null}
                />
              {/if}

              {#if field.help}
                <small>{field.help}</small>
              {/if}
              {#if errors[field.name]}
                <small class="error">{errors[field.name]}</small>
              {/if}
            </label>
          {/each}
        </div>
      {/if}
    </div>

    <div slot="footer" class="actions">
      <button class="secondary" type="button" on:click={close}>{$operatorActionStore.request.cancelText}</button>
      <button
        class:danger={$operatorActionStore.request.danger}
        type="button"
        disabled={Boolean($operatorActionStore.request.blockedReason)}
        on:click={() => submit($operatorActionStore.request)}
      >
        {$operatorActionStore.request.submitText}
      </button>
    </div>
  </Modal>
{/if}

<style>
  .action-modal,
  .fields {
    display: grid;
    gap: 0.9rem;
  }
  .subtitle,
  .blocked-banner,
  small {
    color: var(--text-secondary, #64748b);
  }
  .subtitle {
    margin: 0.35rem 0 0;
  }
  .blocked-banner {
    border: 1px solid #fdba74;
    border-radius: 12px;
    background: #fff7ed;
    color: #9a3412;
    padding: 0.75rem 0.85rem;
  }
  label {
    display: grid;
    gap: 0.35rem;
  }
  input,
  select,
  textarea,
  button {
    font: inherit;
  }
  input,
  select,
  textarea {
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 0.7rem 0.85rem;
    background: #fff;
  }
  textarea {
    resize: vertical;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
  }
  .secondary {
    background: #fff;
    color: #0f172a;
  }
  .danger {
    background: #b91c1c;
    color: #fff;
  }
  .error {
    color: #c61f35;
  }
</style>
