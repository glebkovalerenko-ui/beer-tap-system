# Incident Severity Matrix

| Severity | Примеры событий | Целевое время подтверждения | Целевое время закрытия | Обязательные действия | Кто может закрывать |
|---|---|---:|---:|---|---|
| S1 | emergency_stop, closed_valve_flow, non_sale_flow | 5 мин | 30 мин | acknowledge, note, escalation | shift_lead, engineer_owner |
| S2 | tap_without_keg, report_lost_card | 15 мин | 120 мин | acknowledge, note | shift_lead, engineer_owner |
| S3 | visit_force_unlock, offline_sync_issue | 30 мин | 240 мин | acknowledge, note | operator, shift_lead, engineer_owner |
| S4 | reconcile_pour, low_impact_operational_anomaly | 60 мин | 480 мин | acknowledge, note | operator, shift_lead, engineer_owner |

> Матрица синхронизирована с backend-константой `SEVERITY_MATRIX` в `backend/crud/incident_crud.py`.
