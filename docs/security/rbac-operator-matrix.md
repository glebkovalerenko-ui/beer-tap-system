# RBAC Operator Matrix

## Обозначения

- `allow` — действие разрешено без дополнительных шагов.
- `deny` — действие запрещено.
- `allow+confirm` — действие разрешено только после обязательного подтверждения в UI.
- `allow+2nd-approval` — действие разрешено только после подтверждения исполнителя и второго одобрения (другой пользователь с достаточной ролью).

## Матрица операторских действий

| Действие | Operator | Shift Lead | Engineer |
|---|---|---|---|
| Просмотр статуса кранов, датчиков и связи | allow | allow | allow |
| Просмотр активных сессий розлива | allow | allow | allow |
| Запуск/остановка розлива по сессии | allow | allow | allow |
| Пауза/возобновление розлива (операционная) | allow | allow | allow |
| Просмотр очереди алертов/инцидентов | allow | allow | allow |
| Подтверждение некритичных алертов | allow | allow | allow |
| Ручная калибровка потока по крану (в пределах смены) | deny | allow+confirm | allow |
| Коррекция остатков кеги (inventory adjust) | deny | allow+confirm | allow |
| Перепривязка кеги к крану | deny | allow+confirm | allow |
| Открытие/закрытие смены | deny | allow | allow |
| Ручной refund/компенсация | deny | allow+confirm | allow |
| Сброс/разлогин NFC-сессии пользователя | deny | allow+confirm | allow |
| Изменение лимитов розлива/скорости для смены | deny | allow+confirm | allow |
| Включение maintenance mode на точке | deny | allow+confirm | allow |
| Перезапуск edge-сервиса контроллера (без reboot узла) | deny | allow+confirm | allow |
| **[ОПАСНО] Принудительное открытие клапана (override valve open)** | deny | deny | allow+2nd-approval |
| **[ОПАСНО] Emergency stop всей линии** | allow+confirm | allow+confirm | allow+confirm |
| **[ОПАСНО] Отключение interlock/защитных блокировок** | deny | deny | allow+2nd-approval |
| **[ОПАСНО] Массовый purge/пролив линии** | deny | allow+2nd-approval | allow+confirm |
| **[ОПАСНО] Изменение calibration coefficients вне безопасного диапазона** | deny | deny | allow+2nd-approval |
| **[ОПАСНО] Удалённый restart контроллера/узла** | deny | allow+2nd-approval | allow+confirm |
| **[ОПАСНО] Ротация/отзыв production API key** | deny | deny | allow+2nd-approval |
| **[ОПАСНО] Изменение RBAC ролей и grant elevated access** | deny | deny | allow+2nd-approval |
| **[ОПАСНО] Удаление audit логов или изменение retention** | deny | deny | allow+2nd-approval |

## Дополнительные требования для опасных действий

Для всех действий, помеченных как **[ОПАСНО]**, обязательны:

1. **Обязательное подтверждение**
   - Явный confirm-диалог с повторным вводом контекста действия (например, имя крана/узла).
   - Для `allow+2nd-approval` — двухэтапный workflow: инициатор + отдельный аппрувер.
2. **Reason code**
   - Исполнитель обязан выбрать reason code из справочника (`safety`, `incident-response`, `hardware-fault`, `security`, `other`).
   - Для `other` обязателен свободный текст с пояснением.
3. **Audit trail (кто, когда, откуда, почему)**
   - Кто: `actor_user_id`, `actor_role`, при 2nd approval также `approver_user_id`, `approver_role`.
   - Когда: `requested_at`, `confirmed_at`, `approved_at`, `executed_at` (UTC).
   - Откуда: `source_ip`, `device_id`, `client_app_version`, `site_id`.
   - Почему: `reason_code`, `reason_comment`, `ticket_id`/`incident_id` (если есть).

## Привязка к UI

Для каждого действия матрицы UI должен применять режим отображения по эффективному праву:

- `deny` → действие **скрыть** (если функция не релевантна роли) либо показать **disabled** с подсказкой "Недостаточно прав".
- `allow` → обычная активная кнопка/команда.
- `allow+confirm` → активная кнопка, но выполнение только через confirm-модалку с явным предупреждением.
- `allow+2nd-approval` → кнопка "Запросить выполнение", статус ожидания второго одобрения и явная индикация, кто должен аппрувить.

Рекомендации UX:

- Для опасных действий использовать визуальное выделение (`danger` стиль, иконка риска).
- В confirm-диалоге показывать последствия и условия отката (если доступны).
- Для заблокированных действий показывать детальную причину (роль, требуемое право, required approval).

## Привязка к API (server-side enforcement)

UI-ограничения не являются достаточными; API обязан применять политику независимо от клиента:

1. Проверять `actor_role` и требуемый permission/action на сервере для каждого мутирующего endpoint.
2. Для `allow+confirm` требовать признак подтверждения (например, `confirmed=true` + nonce/TTL).
3. Для `allow+2nd-approval` требовать валидную вторую подпись/approval token от другого пользователя с допустимой ролью.
4. Валидировать наличие `reason_code` (и `reason_comment`, когда `other`).
5. Записывать полный audit trail до и после выполнения опасного действия.
6. Запрещать выполнение при несоответствии контекста (site scope, shift scope, revoked session, expired approval).
7. Возвращать детализированные коды отказа (`403 RBAC_DENY`, `409 APPROVAL_REQUIRED`, `422 REASON_REQUIRED`) для консистентной обработки в UI.

## Минимальная модель прав (рекомендуемая)

- `tap.view`, `tap.pour.control`, `alerts.ack`
- `inventory.adjust`, `tap.rebind`, `session.reset`
- `maintenance.toggle`, `service.restart`
- `safety.emergency_stop`, `safety.override_valve`, `safety.interlock.bypass`
- `system.reboot`, `security.keys.rotate`, `rbac.admin`, `audit.retention.manage`

Матрица ролей должна маппиться на эти granular permissions, а не только на названия ролей, чтобы упростить аудит и эволюцию политики.
