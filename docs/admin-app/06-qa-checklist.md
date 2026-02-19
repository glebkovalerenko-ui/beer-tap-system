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

## Execution notes

- Date:
- Tester:
- Environment:
- Known limitations:
- Go/No-Go decision:
