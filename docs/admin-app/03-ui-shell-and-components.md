# Phase 2 — UI Shell & Design System Lite

## Scope

Документ определяет:
1) глобальный UI shell admin-app,
2) Design System Lite (токены + компоненты + состояния),
3) правила применения в core flows.

Цель — обеспечить быструю и ровную реализацию Фазы 3 без визуального/архитектурного хаоса.

---

## 1) UI Shell spec

## 1.1 Top bar (persistent)

Top bar фиксирован и виден на всех рабочих экранах.

### Left cluster
- Ярлык продукта/локации (точка продаж)
- Заголовок текущего сценария (например, «Пополнение баланса»)

### Center cluster
- **Контекст гостя**:
  - Имя гостя
  - Short card UID
  - Статус гостя (active/blocked)
- Если контекста нет: neutral chip `Гость не выбран`

### Right cluster (operational status)
- **Пилла смены**: Открыта / Закрыта / Требует внимания
- **Пилла сети**: Онлайн / Нестабильно / Офлайн
- **Пилла NFC**: Считыватель готов / Считыватель с ошибкой
- **Бейдж очереди синхронизации**: `Очередь синхронизации: N` (если есть)
- Меню оператора (имя + роль + «Выйти»)

### Contract boundary with screen content

Top bar является единственным местом для стабильного глобального контекста:
- состояние смены (open/close + timestamp),
- текущее время,
- global health/status pills,
- оператор и guest context.

Экранные маршруты (например, `Today`) не должны дублировать эти блоки отдельными карточками сверху.  
Если экрану нужен статус из shell, он должен использовать его как контекст для copy/приоритезации действий, но не как второй источник UI.

## 1.2 Main workspace layout

### Desktop layout
- 12-column grid, content max-width: 1440px, adaptive.
- Основная рабочая колонка (операция) + вспомогательная колонка (контекст/история/подсказки).

### Tablet/touch layout
- Одноколоночный режим с sticky primary CTA в нижней зоне.
- Критичные статусы остаются видимыми (compact top bar).

## 1.3 Screen-level structure

На каждом экране:
1. `Page header` (название операции + короткое описание)
2. `Primary action zone`
3. `Secondary actions zone`
4. `Audit/feedback zone` (последние события/ошибки/тосты)

---

## 2) Design System Lite

## 2.1 Token set (semantic-first)

## Spacing scale
- `sp-1 = 4px`
- `sp-2 = 8px`
- `sp-3 = 12px`
- `sp-4 = 16px`
- `sp-5 = 24px`
- `sp-6 = 32px`
- `sp-7 = 40px`

## Typography scale
- `text-xs = 12/16`
- `text-sm = 14/20`
- `text-md = 16/24` (default body)
- `text-lg = 20/28` (section headers)
- `text-xl = 24/32` (page headers)
- `text-amount = 32/36` (balance/sum emphasis)

## Radius
- `radius-sm = 8px`
- `radius-md = 12px`
- `radius-lg = 16px`

## Elevation
- `elev-0`: flat
- `elev-1`: base cards
- `elev-2`: floating elements (dropdown, sticky action bar)
- `elev-3`: modal / critical overlays

## Semantic colors
- `surface/base`
- `surface/muted`
- `text/primary`, `text/secondary`, `text/inverse`
- `brand/primary`, `brand/primary-hover`
- `success`, `warning`, `error`, `info`
- `border/default`, `border/strong`

## Interaction states
- default
- hover
- pressed
- focus-visible (обязательно)
- disabled
- loading

---

## 2.2 Component specs

## Button

### Variants
- `Primary` — главный CTA экрана
- `Secondary` — поддерживающее действие
- `Ghost` — неразрушающие вторичные действия
- `Danger` — high-risk actions

### Sizes
- `md` (40–44px height)
- `lg` (48–56px для touch-critical)

### Rules
- На экране максимум 1 Primary.
- Loading-state блокирует повторный submit.
- Danger всегда с явной формулировкой действия (`Блокировать карту`).

## Card

### Usage
- Группировка контекста гостя, смены, суммы, истории.

### Anatomy
- Header
- Body
- Footer actions (optional)

## Input

### Variants
- Text
- Search
- Phone
- Number/Amount

### Rules
- Всегда label + helper/error text.
- Ошибки показываются inline, не только toast.

## Amount keypad

### Purpose
Быстрый и безошибочный ввод сумм пополнения.

### Includes
- Preset chips (`200`, `500`, `1000`, ...)
- Numeric keypad `0-9`, `00`, `⌫`
- Текущее значение крупным числом
- CTA `Подтвердить пополнение`

### Rules
- Нельзя ввести невалидный формат.
- Верхний/нижний лимит суммы проверяется до submit.

## Toast / Notification

### Types
- Success
- Warning
- Error
- Info

### Rules
- Success — auto-dismiss (3–5s)
- Error — остается до взаимодействия, если блокирует flow
- Для финансовых success: include action `Отменить` (если поддерживается)

## Modal (high-risk only)

### Use cases
- Block/Reissue confirm
- Close shift confirm
- Emergency irreversible action

### Rules
- Не использовать модалки для частых действий.
- Текст: “что произойдет” + “можно ли отменить”.

## Status pill

### Variants
- `online`
- `offline`
- `degraded`
- `nfc-ok`
- `nfc-error`
- `shift-open`
- `shift-closed`

### Rules
- Цвет + иконка + текст (не только цвет).
- Всегда в top bar.

## Table / list

### Usage
- История операций, журнал инцидентов, список гостей.

### Rules
- Сортировка по времени (новые сверху).
- Пустое состояние + CTA.

## Empty state

### Anatomy
- Заголовок
- 1 строка объяснения
- Главный CTA
- (опционально) Secondary CTA

### Example
“Нет операций по гостю. Выполните первое пополнение.”

---

## 3) Operational UX rules by scenario

## Frequent money operations
- 1–2 экрана максимум.
- Key information above the fold.
- Primary CTA sticky/явный.

## High-risk operations
- Требуют confirm modal.
- Показывают воздействие и объект.
- Логируются с reason/operator/timestamp.

## Degraded mode
- Глобальный баннер + status pills.
- Отключаются только небезопасные действия.
- Read-only и безопасные шаги остаются доступны.

---

## 4) Accessibility baseline

- Touch targets: минимум 44x44px.
- Focus-visible для клавиатурной навигации.
- Контраст минимум WCAG AA.
- Ошибки и статусы имеют текстовые маркеры, не только цвет.

---

## 5) Mapping: components ↔ flows

- Issue/Register → `Input`, `Status pill`, `Modal` (only conflict), `Toast`
- Top up → `Amount keypad`, `Card`, `Primary Button`, `Toast (undo)`
- Balance/history → `Card`, `List/Table`, `Empty state`
- Block/Reissue → `Danger Button`, `Modal`, `Status pill`
- Incidents → `Form Input`, `List`, `Toast`
- Shift open/close → `Status pill`, `Modal`, `Report Card`

---

## 6) Phase 2 handoff checklist

- [x] Описан постоянный shell со статусами смены/сети/NFC/queue.
- [x] Определены Design System Lite токены.
- [x] Зафиксированы компоненты и их usage rules.
- [x] Учтены ограничения touch-first и error-proof UX.
- [x] Подготовлен маппинг компонентов на core flows для реализации.


## 7) UX copy dictionary (Shell + Tap Screens)

Чтобы не возвращались англоязычные вкрапления в операторских экранах, тексты shell и экранов кранов централизованы в `admin-app/src/lib/operatorLabels.js`:

- `SHELL_COPY` — верхняя панель, подписи контекста гостя/оператора, синхронизация и tooltip-подсказки.
- `TAP_SCREENS_COPY` — подписи гостевого предпросмотра, состояния экрана/контроллера, комментариев оператора, сводок и сообщений ошибок.

Правило: для новых экранов и aria/title/tooltip использовать словарь из `operatorLabels.js`, а не хардкодить строки в компонентах.
