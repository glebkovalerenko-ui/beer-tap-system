# Phase 2 — IA + Core Flows Specification

## Scope

Этот документ фиксирует целевую информационную архитектуру `admin-app` и детальные flow-спеки для реализации в Фазе 3.

Принципы:
- operations-first (операции, а не разделы CRUD),
- speed-first (частые действия в 1–2 экрана),
- error-proofing (предотвращение и безопасное восстановление),
- auditability (критичные действия оставляют читаемый след).

---

## 1) Sitemap / IA (5–7 top actions)

## Global shell actions

1. **Identify Guest**
   - Поиск по имени/телефону
   - Скан карты/NFC
2. **Issue Card / Register Guest**
   - Новый гость + привязка карты
   - Существующий гость + новая карта
3. **Top Up Balance**
   - Presets + keypad
   - Confirm + result
4. **Balance & History**
   - Текущий баланс
   - Последние операции
5. **Card Controls**
   - Block card
   - Reissue card + transfer balance
6. **Shift Management**
   - Open shift
   - Close shift + quick report
7. **Incidents & Recovery**
   - Undo last operation (if available)
   - Incident form + next best action

## IA view (logical)

```text
POS Workspace
├─ Guest Context (identified / not identified)
│  ├─ Issue/Register
│  ├─ Top Up
│  ├─ Balance & History
│  └─ Card Controls (block/reissue)
├─ Shift Context (open / closed / blocked)
│  ├─ Open Shift
│  └─ Close Shift + Report
└─ Incident Context
   ├─ Undo last operation
   └─ Incident workflow
```

---

## 2) Core flow specs

## Flow A — Выдать карту / зарегистрировать гостя

### Entry points
- Primary CTA: `Выдать карту`
- Secondary: из пустого состояния “Нет гостя в контексте”

### Steps
1. Открыть мастер “Выдать карту”.
2. Выбрать режим:
   - Новый гость,
   - Существующий гость.
3. Заполнить минимальные поля (для нового): имя, телефон.
4. Поднести карту к NFC.
5. Проверка уникальности карты.
6. Confirm экрана “Гость + UID + действие”.
7. Success state + CTA `Пополнить`.

### Data shown
- Идентификатор гостя (читаемый формат: ФИО + телефон).
- UID карты (с маскированием/сокращением в общем UI).
- Статус reader: online/error.
- Время операции и оператор (после успеха).

### Possible errors
- Карта уже привязана.
- Reader timeout.
- API unavailable.
- Duplicate phone/guest conflict.

### Recovery UX
- “Карта уже используется” → CTA: `Открыть владельца карты`.
- “Reader не отвечает” → CTA: `Повторить скан` / `Проверить NFC`.
- “Сервис недоступен” → CTA: `Сохранить инцидент` / `Повторить`.

---

## Flow B — Пополнение баланса

### Entry points
- Primary CTA в карточке гостя: `Пополнить`
- Быстрый action после успешной выдачи карты

### Steps
1. Открыть экран пополнения для guest context.
2. Выбрать сумму:
   - preset chips,
   - keypad/manual input.
3. Выбрать метод оплаты (MVP: cash default).
4. Проверить summary (гость + карта + сумма + метод).
5. Подтвердить.
6. Показать результат + обновленный баланс + запись в истории.

### Data shown
- Гость (имя/телефон), карта (short UID), текущий баланс.
- Сумма операции (крупная типографика).
- Метод оплаты.
- Пост-фактум: transaction ID, timestamp, оператор.

### Possible errors
- Нулевая/отрицательная сумма.
- Превышение лимита суммы.
- Double-submit.
- Timeout/connection loss.

### Recovery UX
- Клиентская валидация до submit.
- Button loading-lock во время запроса.
- При timeout: “Статус операции неизвестен” + CTA `Проверить историю`.
- Undo таймер (если API поддерживает); иначе `Создать инцидент`.

---

## Flow C — Проверка баланса + история

### Entry points
- Guest context panel
- Поиск/скан карты

### Steps
1. Идентифицировать гостя.
2. Открыть unified экран `Баланс и история`.
3. Просмотреть баланс и последние операции.
4. Выполнить next action: `Пополнить` / `Блокировать` / `Инцидент`.

### Data shown
- Текущий баланс (самый заметный элемент).
- Последние N транзакций (тип, сумма, время, оператор).
- Статус карты/гостя (active/blocked).

### Possible errors
- История не загрузилась.
- Нет транзакций.
- Guest context потерян.

### Recovery UX
- История недоступна: `Обновить` + `Продолжить без истории`.
- Empty state: “Операций пока нет” + CTA `Пополнить`.
- Потеря контекста: `Найти гостя`.

---

## Flow D — Блокировка / перевыпуск / перенос баланса

### Entry points
- Card controls в гостевом профиле

### Steps (block)
1. Нажать `Блокировать карту`.
2. Выбрать причину (утеря/подозрение/другое).
3. High-risk confirm.
4. Success + статус карты `Blocked` + лог.

### Steps (reissue)
1. Нажать `Перевыпустить карту`.
2. Поднести новую карту.
3. Проверить, что карта свободна.
4. Выбрать “перенести баланс” (toggle).
5. Confirm.
6. Success: старая blocked, новая active, баланс перенесен.

### Data shown
- Текущая карта и статус.
- Новая карта (при reissue).
- Баланс до/после переноса.
- Причина и оператор.

### Possible errors
- Новая карта занята.
- Конфликт статусов карт.
- Ошибка переноса баланса.

### Recovery UX
- Карта занята: `Открыть владельца` / `Сканировать другую`.
- Частичное выполнение: clearly marked state + “обязательные шаги завершения”.
- Любой fail фиксируется в incident log.

---

## Flow E — Отмена последней операции / инцидент

### Entry points
- Success toast после финансового действия
- Раздел incidents

### Steps (undo path)
1. После операции показывается toast с `Отменить` и таймером.
2. Оператор жмет `Отменить`.
3. Система подтверждает rollback.
4. Запись в истории как “отменено”.

### Steps (incident path)
1. Открыть `Инцидент`.
2. Выбрать тип инцидента.
3. Привязать к гостю/операции.
4. Добавить комментарий.
5. Сохранить, получить ID инцидента.

### Data shown
- Исходная операция (sum, guest, timestamp).
- Причина инцидента.
- Рекомендуемый next action.

### Possible errors
- Undo недоступен.
- Операция не найдена.
- Невалидный инцидент payload.

### Recovery UX
- Если undo недоступен: явное сообщение + `Создать инцидент`.
- Если инцидент не сохранился: сохранить локально draft + повторная отправка.

---

## Flow F — Открытие/закрытие смены + быстрый отчет

### Entry points
- Shift status widget (global shell)

### Steps (open)
1. Нажать `Открыть смену`.
2. Проверить оператора/точку/время.
3. Подтвердить.
4. Shell показывает `Смена открыта`.

### Steps (close)
1. Нажать `Закрыть смену`.
2. Показать summary:
   - число операций,
   - сумма пополнений,
   - инциденты,
   - несинхронизированные операции.
3. Подтвердить.
4. Получить quick report + финальный статус.

### Data shown
- Shift ID, оператор, open/close timestamps.
- KPI summary.
- Блокирующие условия (если есть).

### Possible errors
- Нет открытой смены при операциях.
- Есть незавершенные инциденты.
- Сервис отчетов недоступен.

### Recovery UX
- Глобальный guard: “Откройте смену для продолжения”.
- При блокировке закрытия: actionable checklist, что нужно закрыть.

---

## 3) Cross-flow recovery standards

## Common error taxonomy
- Validation errors
- Connectivity errors
- Device errors (NFC)
- Permission/role errors
- Unknown/system errors

## Standard recovery actions
- `Повторить`
- `Проверить статус устройств`
- `Открыть контекст гостя`
- `Создать инцидент`
- `Позвать администратора`

## UX constraints
- Не более 1 blocking modal одновременно.
- На каждой ошибке — max 2 рекомендованных действия.
- Никогда не оставлять пользователя в тупике.

---

## 4) Flow acceptance gates (для Фазы 3)

- [ ] A: Выдача карты завершается за ≤ 60 сек без длинной формы.
- [ ] B: Пополнение требует ≤ 5 взаимодействий после открытия экрана.
- [ ] C: Баланс и история доступны на одном экране.
- [ ] D: Блокировка/перевыпуск требуют high-risk confirm и логируются.
- [ ] E: Есть undo/incident путь после денежной операции.
- [ ] F: Shift open/close и quick report отображаются в shell.
- [ ] Все ошибки дают понятный next best action.
