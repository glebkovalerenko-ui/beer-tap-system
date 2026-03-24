# Phase 3 — QA Checklist (Demo-ready Gate)

## Scope

Чеклист предназначен для быстрых итерационных прогонов перед демо и перед merge каждого milestone.

Legend:
- `[ ]` not checked
- `[x]` pass
- `[~]` warning / partial
- `[!]` fail

---

## A. Build & runtime sanity

- [ ] `npm run build` проходит без ошибок.
- [ ] App открывается и не падает на стартовом экране.
- [ ] Login flow работает (валидные и невалидные креды).
- [ ] После login открываются все базовые роуты (`#/`, `#/guests`, `#/taps-kegs`).

---

## B. Shell & navigation

- [ ] Top bar всегда видим на рабочих экранах.
- [ ] Видны статусы: shift / network / NFC.
- [ ] Guest context корректно обновляется при выборе гостя.
- [ ] Выход (logout) работает и сбрасывает защищенную часть UI.

---

## C. Guest context flow

- [ ] Поиск гостя работает по имени/части ФИО.
- [ ] Выбор гостя открывает detail-панель.
- [ ] Empty state (без выбранного гостя) содержит понятный CTA.
- [ ] Создание гостя работает, форма не ломает layout.
- [ ] Редактирование гостя работает.

---

## D. Card binding / NFC

- [ ] Кнопка `Привязать карту` доступна и открывает NFC modal.
- [ ] При успешном read карта привязывается.
- [ ] При NFC ошибке показывается понятное сообщение.
- [ ] Ошибка NFC не блокирует всю страницу.

---

## E. Top-up flow

- [ ] Пополнение блокируется при закрытой смене (guard message).
- [ ] При открытой смене top-up modal открывается.
- [ ] Preset кнопки корректно выставляют сумму.
- [ ] Keypad вводит/удаляет значения корректно.
- [ ] Невалидная сумма показывает inline error.
- [ ] Успешное пополнение обновляет баланс.
- [ ] Повторный submit защищен loading-state.

---

## F. Balance & recent history

- [ ] Блок баланса отображается корректно.
- [ ] История операций отображается при наличии данных.
- [ ] При отсутствии transaction list работает fallback recent pours.
- [ ] Empty fallback содержит next best action и не выглядит как ошибка.

---

## G. Shift workflow

- [ ] `Открыть смену` меняет shift status.
- [ ] `Закрыть смену` возвращает shift status в closed.
- [ ] Summary по shift (count/amount) обновляется после top-up.
- [ ] Shift panel остается читаемым на разных размерах окна.

---

## H. Degraded/demo mode stability

- [ ] Demo mode toggle меняет состояние и сохраняется локально.
- [ ] В demo mode показывается fallback banner.
- [ ] При offline/NFC-error banner показывает actionable текст.
- [ ] Нет hard-crash при частичном отказе сети/API.

---

## I. Visual consistency

- [ ] Основные CTA заметны и единообразны.
- [ ] Нет критичных выравниваний/overflow на 1366x768.
- [ ] Тексты ошибок не обрезаются.
- [ ] Touch-critical кнопки достаточно крупные (>=44px).

### I.1 Contrast checks (WCAG AA)

- [ ] Контраст обычного текста в статусных плашках/баннерах не ниже **4.5:1**.
- [ ] Контраст текста на кнопках со статусной семантикой (success/warning/critical/neutral) не ниже **4.5:1**.
- [ ] Контраст нетекстовых индикаторов (бордеры, бейджи, чипы, прогресс-индикаторы) относительно фона не ниже **3:1**.
- [ ] Проверены состояния `default`, `hover`, `selected`, `disabled` для статусных UI-индикаторов.

---

## J. Regression checks

- [ ] Dashboard emergency stop flow сохранил поведение.
- [ ] Taps/Kegs экран не поломан shell-изменениями.
- [ ] Toast/confirm механика продолжает работать.
- [ ] Polling system/pours не вызывает UI freeze.

---

## K. Pre-demo sign-off

- [ ] Прогнан `05-demo-script.md` end-to-end.
- [ ] Сценарий укладывается в 6–8 минут.
- [ ] Есть fallback-ветка при сбое backend/NFC.
- [ ] Все blockers закрыты или имеют workaround.

---

## L. RBAC smoke matrix (operator / shift_lead / engineer_owner)

Проверить каждый сценарий минимум на 3 ролях, где `403` всегда сопровождается toast:
**«Действие недоступно для текущей роли»**.

| Сценарий | operator | shift_lead | engineer_owner |
| --- | --- | --- | --- |
| Просмотр очереди инцидентов | ✅ | ✅ | ✅ |
| `escalate_incident` / `close_incident` | ❌ (403 + toast) | ✅ | ✅ |
| `set_emergency_stop` | ❌ (403 + toast) | ✅ | ✅ |
| `assign_keg_to_tap` / `unassign_keg_from_tap` / `update_tap` | ❌ (403 + toast) | ✅ | ✅ |
| `update_tap_display_config` (tap screens override) | ❌ (403 + toast) | ❌ (403 + toast) | ✅ |
| `restore_lost_card`, card reissue/bind flows | ❌ (403 + toast) | ✅ | ✅ |

Минимальные шаги smoke для каждой строки:
1. Войти под целевой ролью.
2. Выполнить action из UI (или через bridge-инициированное действие).
3. Подтвердить, что backend возвращает ожидаемый статус (`200/201` или `403`).
4. Для `403` убедиться в едином UX: toast с текстом про недоступность действия для текущей роли.
5. Проверить отсутствие побочного изменения данных после `403`.

---

## Execution notes

- Date:
- Tester:
- Environment:
- Known limitations:
- Go/No-Go decision:
