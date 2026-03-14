<script>
  import { createEventDispatcher, onMount } from 'svelte';

  import MediaAssetPicker from '../display/MediaAssetPicker.svelte';
  import { normalizeError } from '../../lib/errorUtils.js';
  import { formatTapStatus } from '../../lib/formatters.js';
  import { tapStore } from '../../stores/tapStore.js';
  import { uiStore } from '../../stores/uiStore.js';

  export let tap;

  const dispatch = createEventDispatcher();

  const DEFAULT_ACCENT_COLOR = '#C79A3B';
  const DEFAULT_FALLBACK_TITLE = 'Кран недоступен';
  const DEFAULT_FALLBACK_SUBTITLE = 'Обратитесь к оператору';
  const DEFAULT_MAINTENANCE_TITLE = 'Кран временно недоступен';
  const DEFAULT_MAINTENANCE_SUBTITLE = 'Обратитесь к оператору';

  let loading = true;
  let saving = false;
  let loadError = '';
  let formError = '';
  let formData = createEmptyForm();

  $: beverage = tap?.keg?.beverage ?? null;
  $: effectiveAccentColor = isHexColor(formData.override_accent_color)
    ? formData.override_accent_color
    : beverage?.accent_color || DEFAULT_ACCENT_COLOR;
  $: effectivePriceMode = formData.show_price_mode || beverage?.price_display_mode_default || 'per_100ml';
  $: effectiveBackgroundSource = formData.override_background_asset_id
    ? 'Переопределен на уровне крана'
    : beverage?.background_asset_id
      ? 'Наследуется от напитка'
      : 'Фон не задан';

  onMount(() => {
    loadConfig();
  });

  function createEmptyForm() {
    return {
      enabled: true,
      fallback_title: '',
      fallback_subtitle: '',
      maintenance_title: '',
      maintenance_subtitle: '',
      override_accent_color: '',
      override_background_asset_id: null,
      show_price_mode: '',
    };
  }

  function normalizeOptionalString(value) {
    const normalized = String(value ?? '').trim();
    return normalized || null;
  }

  function isHexColor(value) {
    return /^#[0-9a-fA-F]{6}$/.test(String(value || '').trim());
  }

  function getAccentPreviewColor() {
    return isHexColor(formData.override_accent_color) ? formData.override_accent_color : effectiveAccentColor;
  }

  function formatPriceModeLabel(mode) {
    if (mode === 'per_liter') {
      return '₽ / л';
    }

    if (mode === 'per_100ml') {
      return '₽ / 100 мл';
    }

    return 'Наследуется';
  }

  function mapConfigToForm(config) {
    return {
      enabled: config?.enabled ?? true,
      fallback_title: config?.fallback_title || '',
      fallback_subtitle: config?.fallback_subtitle || '',
      maintenance_title: config?.maintenance_title || '',
      maintenance_subtitle: config?.maintenance_subtitle || '',
      override_accent_color: config?.override_accent_color || '',
      override_background_asset_id: config?.override_background_asset_id || null,
      show_price_mode: config?.show_price_mode || '',
    };
  }

  function buildPayload() {
    return {
      enabled: Boolean(formData.enabled),
      fallback_title: normalizeOptionalString(formData.fallback_title),
      fallback_subtitle: normalizeOptionalString(formData.fallback_subtitle),
      maintenance_title: normalizeOptionalString(formData.maintenance_title),
      maintenance_subtitle: normalizeOptionalString(formData.maintenance_subtitle),
      override_accent_color: normalizeOptionalString(formData.override_accent_color),
      override_background_asset_id: formData.override_background_asset_id || null,
      show_price_mode: normalizeOptionalString(formData.show_price_mode),
    };
  }

  function updateAccentColor(value) {
    formData = {
      ...formData,
      override_accent_color: value,
    };
  }

  function clearAccentColor() {
    formData = {
      ...formData,
      override_accent_color: '',
    };
  }

  async function loadConfig() {
    if (!tap?.tap_id) {
      loadError = 'Не удалось определить кран для настройки экрана.';
      loading = false;
      return;
    }

    loading = true;
    loadError = '';
    try {
      const config = await tapStore.fetchTapDisplayConfig(tap.tap_id);
      formData = mapConfigToForm(config);
    } catch (error) {
      loadError = normalizeError(error);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    formError = '';
    saving = true;

    try {
      const savedConfig = await tapStore.updateTapDisplayConfig(tap.tap_id, buildPayload());
      formData = mapConfigToForm(savedConfig);
      uiStore.notifySuccess(`Настройки экрана для «${tap.display_name}» сохранены.`);
      dispatch('saved', { config: savedConfig });
    } catch (error) {
      formError = normalizeError(error);
    } finally {
      saving = false;
    }
  }
</script>

<div class="tap-display-settings">
  <div class="modal-title">
    <h3>Экран крана {tap.display_name}</h3>
    <p>Настройте сервисные тексты и переопределения, которые работают поверх контента напитка.</p>
  </div>

  {#if loading}
    <p class="state-message">Загружаем настройки экрана...</p>
  {:else if loadError}
    <div class="state-message error-block">
      <p>{loadError}</p>
      <button type="button" class="secondary-action" on:click={loadConfig}>Повторить</button>
    </div>
  {:else}
    <div class="summary-grid">
      <div class="summary-card">
        <span class="label">Статус крана</span>
        <strong>{formatTapStatus(tap.status)}</strong>
      </div>
      <div class="summary-card">
        <span class="label">Напиток по умолчанию</span>
        <strong>{beverage?.name || 'Не назначен'}</strong>
      </div>
      <div class="summary-card">
        <span class="label">Текущий режим цены</span>
        <strong>{formatPriceModeLabel(effectivePriceMode)}</strong>
      </div>
      <div class="summary-card">
        <span class="label">Акцент</span>
        <div class="accent-meta">
          <span class="accent-dot" style={`background:${effectiveAccentColor}`}></span>
          <strong>{effectiveAccentColor}</strong>
        </div>
      </div>
    </div>

    <fieldset class="toggle-block">
      <label class="toggle-row">
        <input type="checkbox" bind:checked={formData.enabled} disabled={saving} />
        <div>
          <span>Показывать Tap Display для этого крана</span>
          <small>Если отключить экран, кран будет показываться как временно недоступный.</small>
        </div>
      </label>
    </fieldset>

    <fieldset>
      <legend>Fallback для пустого или недоступного крана</legend>
      <div class="form-grid">
        <label>
          <span>Заголовок</span>
          <input
            type="text"
            placeholder={DEFAULT_FALLBACK_TITLE}
            bind:value={formData.fallback_title}
            disabled={saving}
          />
        </label>

        <label>
          <span>Подзаголовок</span>
          <textarea
            rows="3"
            placeholder={DEFAULT_FALLBACK_SUBTITLE}
            bind:value={formData.fallback_subtitle}
            disabled={saving}
          ></textarea>
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Текст для обслуживания и блокировки</legend>
      <div class="form-grid">
        <label>
          <span>Заголовок обслуживания</span>
          <input
            type="text"
            placeholder={DEFAULT_MAINTENANCE_TITLE}
            bind:value={formData.maintenance_title}
            disabled={saving}
          />
        </label>

        <label>
          <span>Подзаголовок обслуживания</span>
          <textarea
            rows="3"
            placeholder={DEFAULT_MAINTENANCE_SUBTITLE}
            bind:value={formData.maintenance_subtitle}
            disabled={saving}
          ></textarea>
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Переопределения на уровне крана</legend>
      <div class="form-grid">
        <label>
          <span>Акцентный цвет крана</span>
          <small>Оставьте пустым, чтобы наследовать цвет напитка.</small>
          <div class="color-row">
            <input
              class="color-picker"
              type="color"
              value={getAccentPreviewColor()}
              on:input={(event) => updateAccentColor(event.currentTarget.value)}
              disabled={saving}
            />
            <input
              type="text"
              placeholder="Наследовать цвет напитка"
              bind:value={formData.override_accent_color}
              disabled={saving}
            />
            <button type="button" class="secondary-action clear-action" on:click={clearAccentColor} disabled={saving}>
              Сбросить
            </button>
          </div>
        </label>

        <label>
          <span>Показывать цену как</span>
          <small>Оставьте «Без переопределения», чтобы использовать режим напитка.</small>
          <select bind:value={formData.show_price_mode} disabled={saving}>
            <option value="">Без переопределения</option>
            <option value="per_100ml">₽ / 100 мл</option>
            <option value="per_liter">₽ / л</option>
          </select>
        </label>

        <div class="wide">
          <MediaAssetPicker
            kind="background"
            title="Фон Tap Display"
            description="Можно задать отдельный фон только для этого крана. Если оставить пустым, будет использоваться фон напитка."
            selectedAssetId={formData.override_background_asset_id}
            disabled={saving}
            emptyLabel="Фон крана не переопределен"
            on:change={(event) => {
              formData = {
                ...formData,
                override_background_asset_id: event.detail.assetId,
              };
            }}
          />
        </div>
      </div>
    </fieldset>

    <div class="visibility-card">
      <h4>Что увидит оператор</h4>
      <p>
        <strong>Обычный экран:</strong> {beverage?.name || 'Напиток не назначен'} · {formatPriceModeLabel(effectivePriceMode)}
      </p>
      <p>
        <strong>Fallback:</strong> {formData.fallback_title || DEFAULT_FALLBACK_TITLE}
      </p>
      <p>
        <strong>Обслуживание:</strong> {formData.maintenance_title || DEFAULT_MAINTENANCE_TITLE}
      </p>
      <p>
        <strong>Фон:</strong> {effectiveBackgroundSource}
      </p>
    </div>

    <div class="actions">
      <button type="button" class="secondary-action" on:click={() => dispatch('cancel')} disabled={saving}>
        Отмена
      </button>
      <button type="button" on:click={handleSave} disabled={saving}>
        {saving ? 'Сохранение...' : 'Сохранить настройки экрана'}
      </button>
    </div>

    {#if formError}
      <p class="error-text">{formError}</p>
    {/if}
  {/if}
</div>

<style>
  .tap-display-settings {
    display: grid;
    gap: 1rem;
  }

  .modal-title h3,
  .visibility-card h4 {
    margin: 0;
  }

  .modal-title p,
  .visibility-card p {
    margin: 0.3rem 0 0;
    color: var(--text-secondary);
    line-height: 1.45;
  }

  .state-message {
    margin: 0;
    color: var(--text-secondary);
  }

  .error-block {
    display: grid;
    gap: 0.75rem;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
  }

  .summary-card,
  fieldset,
  .visibility-card {
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    background: #fbfcfe;
  }

  .summary-card {
    padding: 0.85rem 0.95rem;
    display: grid;
    gap: 0.3rem;
  }

  .label {
    font-size: 0.84rem;
    color: var(--text-secondary);
  }

  .accent-meta {
    display: flex;
    gap: 0.45rem;
    align-items: center;
  }

  .accent-dot {
    width: 14px;
    height: 14px;
    border-radius: 999px;
    border: 1px solid rgba(0, 0, 0, 0.12);
  }

  fieldset {
    margin: 0;
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
  }

  legend {
    padding: 0 0.4rem;
    font-weight: 700;
  }

  .toggle-block {
    background: #f7fbf8;
  }

  .toggle-row {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.75rem;
    align-items: flex-start;
  }

  .toggle-row span {
    display: block;
    font-weight: 700;
  }

  .toggle-row small,
  label small {
    color: var(--text-secondary);
    line-height: 1.4;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
  }

  label {
    display: grid;
    gap: 0.35rem;
  }

  label span {
    font-weight: 700;
  }

  textarea {
    min-height: 90px;
    resize: vertical;
  }

  .color-row {
    display: grid;
    grid-template-columns: 56px 1fr auto;
    gap: 0.5rem;
    align-items: center;
  }

  .color-picker {
    padding: 0.2rem;
    min-height: 42px;
  }

  .secondary-action {
    width: auto;
    margin: 0;
    background: #edf2fb;
    color: #23416b;
  }

  .clear-action {
    background: #f3f4f6;
    color: #49566d;
  }

  .wide {
    grid-column: 1 / -1;
  }

  .visibility-card {
    padding: 1rem;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .error-text {
    margin: 0;
    color: #c61f35;
  }

  @media (max-width: 860px) {
    .form-grid {
      grid-template-columns: 1fr;
    }

    .color-row {
      grid-template-columns: 56px 1fr;
    }

    .clear-action {
      grid-column: 1 / -1;
    }
  }
</style>
