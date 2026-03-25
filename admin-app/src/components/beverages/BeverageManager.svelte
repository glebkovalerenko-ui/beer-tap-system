<script>
  import MediaAssetPicker from "../display/MediaAssetPicker.svelte";
  import { beverageStore } from "../../stores/beverageStore.js";
  import { uiStore } from "../../stores/uiStore.js";
  import { normalizeError } from "../../lib/errorUtils.js";

  const DEFAULT_ACCENT_COLOR = "#C79A3B";
  export let canManage = true;

  const createEmptyForm = () => ({
    name: "",
    brewery: "",
    style: "",
    abv: "",
    sell_price_per_liter: "450.00",
    display_brand_name: "",
    description_short: "",
    accent_color: DEFAULT_ACCENT_COLOR,
    text_theme: "",
    price_display_mode_default: "per_100ml",
    background_asset_id: null,
    logo_asset_id: null,
  });

  let selectedBeverageId = null;
  let formData = createEmptyForm();
  let formError = "";

  $: beverages = $beverageStore.beverages;
  $: selectedBeverage = beverages.find((item) => item.beverage_id === selectedBeverageId) || null;
  $: submitLabel = selectedBeverage ? "Сохранить изменения" : "+ Добавить напиток";
  $: formTitle = selectedBeverage ? "Редактирование напитка" : "Новый напиток";

  function normalizeOptionalString(value) {
    const normalized = String(value ?? "").trim();
    return normalized || null;
  }

  function isHexColor(value) {
    return /^#[0-9a-fA-F]{6}$/.test(String(value || "").trim());
  }

  function getAccentPreviewColor() {
    return isHexColor(formData.accent_color) ? formData.accent_color : DEFAULT_ACCENT_COLOR;
  }

  function resetForm() {
    formData = createEmptyForm();
  }

  function startCreateMode() {
    if (!canManage) {
      return;
    }
    selectedBeverageId = null;
    formError = "";
    resetForm();
  }

  function selectBeverage(beverage) {
    selectedBeverageId = beverage.beverage_id;
    formError = "";
    formData = {
      name: beverage.name || "",
      brewery: beverage.brewery || "",
      style: beverage.style || "",
      abv: beverage.abv || "",
      sell_price_per_liter: beverage.sell_price_per_liter || "",
      display_brand_name: beverage.display_brand_name || "",
      description_short: beverage.description_short || "",
      accent_color: beverage.accent_color || DEFAULT_ACCENT_COLOR,
      text_theme: beverage.text_theme || "",
      price_display_mode_default: beverage.price_display_mode_default || "per_100ml",
      background_asset_id: beverage.background_asset_id || null,
      logo_asset_id: beverage.logo_asset_id || null,
    };
  }

  function updateAccentColor(value) {
    formData = {
      ...formData,
      accent_color: value,
    };
  }

  function clearAccentColor() {
    formData = {
      ...formData,
      accent_color: "",
    };
  }

  function buildPayload() {
    return {
      name: String(formData.name || "").trim(),
      brewery: normalizeOptionalString(formData.brewery),
      style: normalizeOptionalString(formData.style),
      abv: normalizeOptionalString(formData.abv),
      sell_price_per_liter: String(formData.sell_price_per_liter || "").trim(),
      display_brand_name: normalizeOptionalString(formData.display_brand_name),
      description_short: normalizeOptionalString(formData.description_short),
      accent_color: normalizeOptionalString(formData.accent_color),
      text_theme: normalizeOptionalString(formData.text_theme),
      price_display_mode_default: normalizeOptionalString(formData.price_display_mode_default),
      background_asset_id: formData.background_asset_id || null,
      logo_asset_id: formData.logo_asset_id || null,
    };
  }

  async function handleSubmit() {
    if (!canManage) {
      return;
    }
    const payload = buildPayload();
    formError = "";

    if (!payload.name) {
      formError = "Укажите название напитка.";
      return;
    }

    if (!payload.sell_price_per_liter) {
      formError = "Укажите цену за литр.";
      return;
    }

    try {
      if (selectedBeverageId) {
        const updated = await beverageStore.updateBeverage(selectedBeverageId, payload);
        selectBeverage(updated);
        uiStore.notifySuccess(`Tap Display для напитка «${updated.name}» обновлен.`);
      } else {
        const created = await beverageStore.createBeverage(payload);
        if (created) {
          selectBeverage(created);
          uiStore.notifySuccess(`Напиток «${created.name}» добавлен в справочник.`);
        } else {
          startCreateMode();
          uiStore.notifySuccess("Напиток добавлен в справочник.");
        }
      }
    } catch (error) {
      formError = normalizeError(error);
    }
  }
</script>

<div class="beverage-manager">
  <div class="manager-toolbar">
    <div>
      <h3>Справочник напитков</h3>
      <p>Выберите напиток, чтобы настроить его карточку для Tap Display.</p>
    </div>
    <button type="button" class="secondary-action" on:click={startCreateMode} disabled={!canManage}>
      Новый напиток
    </button>
  </div>

  <div class="beverage-list">
    {#if $beverageStore.loading && beverages.length === 0}
      <p class="placeholder-text">Загрузка напитков...</p>
    {:else if beverages.length === 0}
      <p class="placeholder-text">Напитки еще не добавлены. Создайте первый напиток ниже.</p>
    {:else}
      <ul>
        {#each beverages as beverage (beverage.beverage_id)}
          <li>
            <button
              type="button"
              class:selected={beverage.beverage_id === selectedBeverageId}
              on:click={() => selectBeverage(beverage)}
            >
              <div class="beverage-copy">
                <span class="name">{beverage.name}</span>
                <span class="subtitle">
                  {[beverage.display_brand_name || beverage.brewery, beverage.style].filter(Boolean).join(" • ") || "Без подписи для экрана"}
                </span>
              </div>
              <div class="beverage-meta">
                <span class="type">{beverage.price_display_mode_default || "per_100ml"}</span>
                <span class="price">{beverage.sell_price_per_liter} ₽/л</span>
              </div>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  {#if !canManage}
    <p class="placeholder-text read-only-note">Текущая роль может только просматривать каталог напитков.</p>
  {/if}

  <form class="beverage-form" on:submit|preventDefault={handleSubmit}>
    <div class="form-header">
      <div>
        <h4>{formTitle}</h4>
        <p>
          {#if selectedBeverage}
            Здесь редактируется общая карточка напитка, которую затем используют назначенные краны.
          {:else}
            Создайте карточку напитка и сразу заполните поля, которые увидит гость на Tap Display.
          {/if}
        </p>
      </div>
      {#if selectedBeverage}
        <button type="button" class="secondary-action" on:click={startCreateMode} disabled={!canManage}>
          Новый напиток
        </button>
      {/if}
    </div>

    <fieldset>
      <legend>Карточка напитка</legend>
      <div class="form-grid">
        <label>
          <span>Название для гостя</span>
          <small>В MVP это же название используется и в общем справочнике напитков.</small>
          <input
            type="text"
            placeholder="Например, Heineken"
            bind:value={formData.name}
            required
            disabled={$beverageStore.loading || !canManage}
          />
        </label>

        <label>
          <span>Бренд на экране</span>
          <small>Показывается как отдельная подпись над стилем или вместо пивоварни.</small>
          <input
            type="text"
            placeholder="Например, BrewDog"
            bind:value={formData.display_brand_name}
            disabled={$beverageStore.loading || !canManage}
          />
        </label>

        <label>
          <span>Пивоварня</span>
          <small>Служебная информация для оператора и fallback-подпись на экране.</small>
          <input
            type="text"
            placeholder="Например, Балтика"
            bind:value={formData.brewery}
            disabled={$beverageStore.loading || !canManage}
          />
        </label>

        <label>
          <span>Стиль</span>
          <small>Свободный текст: IPA, Lager, Stout и т.д.</small>
          <input
            type="text"
            placeholder="Например, IPA"
            bind:value={formData.style}
            disabled={$beverageStore.loading || !canManage}
          />
        </label>

        <label>
          <span>Крепость ABV</span>
          <small>Можно оставить пустым, если на экране крепость не нужна.</small>
          <input
            type="text"
            placeholder="Например, 5.0"
            bind:value={formData.abv}
            pattern="^\d*\.?\d*$"
            title="Например, 5.0 или 4.5"
            disabled={$beverageStore.loading || !canManage}
          />
        </label>

        <label>
          <span>Цена за литр</span>
          <small>Основа для расчета гостевой цены на Tap Display.</small>
          <input
            type="text"
            placeholder="Например, 450.00"
            bind:value={formData.sell_price_per_liter}
            required
            pattern="^\d*\.?\d*$"
            title="Например, 450.00 или 500"
            disabled={$beverageStore.loading || !canManage}
          />
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Контент Tap Display</legend>
      <div class="form-grid">
        <label class="wide">
          <span>Короткое описание</span>
          <small>Короткий текст для гостя на основном экране. Лучше без технологического жаргона.</small>
          <textarea
            rows="3"
            maxlength="160"
            placeholder="Например, Легкий лагер с мягкой хмелевой горчинкой."
            bind:value={formData.description_short}
            disabled={$beverageStore.loading || !canManage}
          ></textarea>
        </label>

        <label>
          <span>Акцентный цвет</span>
          <small>Используется в цветовых акцентах экрана.</small>
          <div class="color-row">
            <input
              class="color-picker"
              type="color"
              value={getAccentPreviewColor()}
              on:input={(event) => updateAccentColor(event.currentTarget.value)}
              disabled={$beverageStore.loading || !canManage}
            />
            <input
              type="text"
              placeholder="#C79A3B"
              bind:value={formData.accent_color}
              disabled={$beverageStore.loading || !canManage}
            />
            <button type="button" class="clear-action" on:click={clearAccentColor} disabled={$beverageStore.loading || !canManage}>
              Сбросить
            </button>
          </div>
        </label>

        <label>
          <span>Тема текста</span>
          <small>Если не уверены, оставьте «По умолчанию».</small>
          <select bind:value={formData.text_theme} disabled={$beverageStore.loading || !canManage}>
            <option value="">По умолчанию</option>
            <option value="dark">Темная</option>
            <option value="light">Светлая</option>
          </select>
        </label>

        <label>
          <span>Как показывать цену</span>
          <small>Это режим по умолчанию для напитка; при необходимости его можно переопределить на уровне крана.</small>
          <select bind:value={formData.price_display_mode_default} disabled={$beverageStore.loading || !canManage}>
            <option value="per_100ml">₽ / 100 мл</option>
            <option value="per_liter">₽ / л</option>
            <option value="auto">Авто</option>
          </select>
        </label>

        <div class="wide media-grid">
          <MediaAssetPicker
            kind="background"
            title="Фон Tap Display"
            description="Большое фоновое изображение для основного экрана напитка."
            selectedAssetId={formData.background_asset_id}
            disabled={$beverageStore.loading || !canManage}
            emptyLabel="Фон не выбран"
            on:change={(event) => {
              formData = {
                ...formData,
                background_asset_id: event.detail.assetId,
              };
            }}
          />

          <MediaAssetPicker
            kind="logo"
            title="Логотип напитка"
            description="Небольшой логотип или знак бренда поверх основного фона."
            selectedAssetId={formData.logo_asset_id}
            disabled={$beverageStore.loading || !canManage}
            emptyLabel="Логотип не выбран"
            on:change={(event) => {
              formData = {
                ...formData,
                logo_asset_id: event.detail.assetId,
              };
            }}
          />
        </div>
      </div>
    </fieldset>

    <button type="submit" disabled={$beverageStore.loading || !canManage}>
      {$beverageStore.loading ? "Сохранение..." : submitLabel}
    </button>

    {#if formError}
      <p class="error">{formError}</p>
    {/if}
  </form>
</div>

<style>
  .beverage-manager {
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    background: var(--bg-surface);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .manager-toolbar,
  .form-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .manager-toolbar {
    padding: 1rem;
    border-bottom: 1px solid var(--border-soft);
    background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);
  }

  .manager-toolbar h3,
  .form-header h4 {
    margin: 0;
  }

  .manager-toolbar p,
  .form-header p {
    margin: 0.25rem 0 0;
    color: var(--text-secondary);
    font-size: 0.92rem;
  }

  .secondary-action {
    width: auto;
    margin: 0;
    background: #edf2fb;
    color: #23416b;
  }

  .beverage-list {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border-soft);
    max-height: 260px;
    overflow-y: auto;
    background: #fbfcfe;
  }

  .beverage-list ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.5rem;
  }

  .beverage-list li {
    margin: 0;
  }

  .beverage-list button {
    width: 100%;
    margin: 0;
    padding: 0.85rem 0.9rem;
    background: #fff;
    color: inherit;
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    text-align: left;
    box-shadow: none;
  }

  .beverage-list button.selected {
    border-color: #8bb0f1;
    background: #eef5ff;
  }

  .beverage-copy,
  .beverage-meta {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .beverage-meta {
    align-items: flex-end;
    justify-content: center;
    text-align: right;
  }

  .name {
    font-weight: 700;
    color: var(--text-primary);
  }

  .subtitle,
  .type {
    font-size: 0.82rem;
    color: var(--text-secondary);
  }

  .price {
    font-size: 0.86rem;
    font-weight: 700;
    color: #1c4d88;
  }

  .placeholder-text {
    margin: 0;
    padding: 0.5rem;
    text-align: center;
    color: var(--text-secondary);
  }

  .beverage-form {
    padding: 1rem;
    display: grid;
    gap: 1rem;
  }

  fieldset {
    margin: 0;
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 1rem;
    display: grid;
    gap: 0.85rem;
  }

  legend {
    padding: 0 0.4rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.85rem;
  }

  label {
    display: grid;
    gap: 0.35rem;
    font-size: 0.9rem;
    color: var(--text-primary);
  }

  label span {
    font-weight: 700;
  }

  label small {
    color: var(--text-secondary);
    line-height: 1.35;
  }

  .wide {
    grid-column: 1 / -1;
  }

  textarea {
    min-height: 96px;
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

  .clear-action {
    width: auto;
    margin: 0;
    background: #f3f4f6;
    color: #49566d;
  }

  .media-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .error {
    margin: 0;
    color: #c61f35;
    font-size: 0.88rem;
  }

  @media (max-width: 960px) {
    .manager-toolbar,
    .form-header {
      flex-direction: column;
      align-items: stretch;
    }

    .form-grid {
      grid-template-columns: 1fr;
    }

    .media-grid {
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
