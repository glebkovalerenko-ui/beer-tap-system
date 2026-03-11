use crate::nfc_handler;
use crate::{AppError, CardStatusPayload};
use log::{error, info, warn};
use pcsc::{Context, Error, ReaderState, Scope, State};
use serde::Serialize;
use std::ffi::CString;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};

const CARD_STATUS_CHANGED_EVENT: &str = "card-status-changed";
const READER_STATE_CHANGED_EVENT: &str = "reader-state-changed";
const STATUS_CHANGE_TIMEOUT: Duration = Duration::from_secs(2);
const INITIAL_RECOVERY_BACKOFF: Duration = Duration::from_millis(500);
const MAX_RECOVERY_BACKOFF: Duration = Duration::from_secs(4);
const MIN_SCANNING_REEMIT_DELAY: Duration = Duration::from_millis(300);
const READER_UNAVAILABLE_MESSAGE: &str =
    "Считыватель NFC недоступен. Подключите устройство или дождитесь восстановления.";
const READER_RECOVERING_MESSAGE: &str =
    "Восстанавливаем подключение к NFC-считывателю. Операция продолжится автоматически.";

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ReaderLifecycleState {
    Disconnected,
    Scanning,
    Ready,
    CardPresent,
    Recovering,
    Error,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct ReaderStatePayload {
    pub state: ReaderLifecycleState,
    pub reader_name: Option<String>,
    pub message: Option<String>,
    pub recovering: bool,
    pub card_present: bool,
}

impl ReaderStatePayload {
    fn scanning(message: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::Scanning,
            reader_name: None,
            message: Some(message.into()),
            recovering: false,
            card_present: false,
        }
    }

    fn disconnected(reader_name: Option<String>, message: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::Disconnected,
            reader_name,
            message: Some(message.into()),
            recovering: false,
            card_present: false,
        }
    }

    fn ready(reader_name: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::Ready,
            reader_name: Some(reader_name.into()),
            message: Some("Считыватель готов к работе.".to_string()),
            recovering: false,
            card_present: false,
        }
    }

    fn card_present(reader_name: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::CardPresent,
            reader_name: Some(reader_name.into()),
            message: Some("Карта обнаружена.".to_string()),
            recovering: false,
            card_present: true,
        }
    }

    fn recovering(reader_name: Option<String>, message: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::Recovering,
            reader_name,
            message: Some(message.into()),
            recovering: true,
            card_present: false,
        }
    }

    fn error(reader_name: Option<String>, message: impl Into<String>) -> Self {
        Self {
            state: ReaderLifecycleState::Error,
            reader_name,
            message: Some(message.into()),
            recovering: false,
            card_present: false,
        }
    }
}

enum MonitorControl {
    Rescan,
}

enum ProbeControl {
    Continue,
    Rescan,
}

struct EmittedReaderState {
    payload: ReaderStatePayload,
    emitted_at: Instant,
}

pub struct ReaderManager {
    command_context: Mutex<Option<Context>>,
    latest_reader_state: Mutex<ReaderStatePayload>,
    last_emitted_reader_state: Mutex<Option<EmittedReaderState>>,
}

impl ReaderManager {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            command_context: Mutex::new(None),
            latest_reader_state: Mutex::new(ReaderStatePayload::scanning(
                "Идет запуск NFC-подсистемы.",
            )),
            last_emitted_reader_state: Mutex::new(None),
        })
    }

    pub fn start(self: &Arc<Self>, app_handle: AppHandle) {
        let manager = Arc::clone(self);
        thread::spawn(move || manager.run(app_handle));
    }

    pub fn get_reader_state(&self) -> ReaderStatePayload {
        self.latest_reader_state.lock().unwrap().clone()
    }

    pub fn get_command_context(&self) -> Result<Context, AppError> {
        {
            let slot = self.command_context.lock().unwrap();
            if let Some(context) = slot.as_ref() {
                if context.is_valid().is_ok() {
                    return Ok(context.clone());
                }
            }
        }

        let context = Context::establish(Scope::User).map_err(AppError::from)?;
        let mut slot = self.command_context.lock().unwrap();
        *slot = Some(context.clone());
        info!("NFC: создан новый контекст PC/SC для командного доступа.");
        Ok(context)
    }

    fn run(self: Arc<Self>, app_handle: AppHandle) {
        let mut last_reader_state_json = String::new();
        let mut last_card_status_json = String::new();
        let mut recovery_backoff = INITIAL_RECOVERY_BACKOFF;
        let mut context_recreate_pending = false;

        self.emit_reader_state(
            &app_handle,
            &mut last_reader_state_json,
            ReaderStatePayload::scanning("Идет поиск NFC-считывателя."),
        );
        self.emit_card_status(
            &app_handle,
            &mut last_card_status_json,
            CardStatusPayload {
                uid: None,
                error: None,
            },
        );

        loop {
            match Context::establish(Scope::User) {
                Ok(context) => {
                    self.store_command_context(Some(context.clone()));
                    recovery_backoff = INITIAL_RECOVERY_BACKOFF;
                    if context_recreate_pending {
                        info!(
                            "NFC: контекст PC/SC пересоздан, мониторинг считывателя возобновлен."
                        );
                        context_recreate_pending = false;
                    } else {
                        info!("NFC: контекст PC/SC установлен.");
                    }

                    self.emit_reader_state(
                        &app_handle,
                        &mut last_reader_state_json,
                        ReaderStatePayload::scanning("Идет поиск NFC-считывателя."),
                    );

                    match self.run_context_session(
                        &app_handle,
                        &context,
                        &mut last_reader_state_json,
                        &mut last_card_status_json,
                    ) {
                        Ok(()) => {}
                        Err(err) => {
                            self.handle_runtime_error(
                                &app_handle,
                                &mut last_reader_state_json,
                                &mut last_card_status_json,
                                err,
                            );
                            context_recreate_pending = true;
                        }
                    }
                }
                Err(err) => {
                    let message = format!("Не удалось создать контекст PC/SC: {}", err);
                    warn!("NFC: {}", message);
                    self.store_command_context(None);
                    context_recreate_pending = true;
                    self.emit_reader_state(
                        &app_handle,
                        &mut last_reader_state_json,
                        ReaderStatePayload::recovering(None, message),
                    );
                    self.emit_card_status(
                        &app_handle,
                        &mut last_card_status_json,
                        CardStatusPayload {
                            uid: None,
                            error: Some(READER_RECOVERING_MESSAGE.to_string()),
                        },
                    );
                }
            }

            thread::sleep(recovery_backoff);
            recovery_backoff = next_backoff(recovery_backoff);
        }
    }

    fn run_context_session(
        &self,
        app_handle: &AppHandle,
        context: &Context,
        last_reader_state_json: &mut String,
        last_card_status_json: &mut String,
    ) -> Result<(), Error> {
        let mut preferred_reader_name: Option<String> = None;

        loop {
            context.is_valid()?;

            let readers = nfc_handler::list_readers_internal(context)?;
            if readers.is_empty() {
                self.emit_reader_state(
                    app_handle,
                    last_reader_state_json,
                    ReaderStatePayload::disconnected(
                        None,
                        "Считыватель NFC не найден. Идет поиск подключения.",
                    ),
                );
                self.emit_card_status(
                    app_handle,
                    last_card_status_json,
                    CardStatusPayload {
                        uid: None,
                        error: Some(READER_UNAVAILABLE_MESSAGE.to_string()),
                    },
                );

                if self.wait_for_topology_change(context)? {
                    self.emit_reader_state(
                        app_handle,
                        last_reader_state_json,
                        ReaderStatePayload::scanning("Идет повторное обнаружение NFC-считывателя."),
                    );
                }
                continue;
            }

            let reader_name = choose_reader_name(&readers, preferred_reader_name.as_deref());
            preferred_reader_name = Some(reader_name.clone());

            info!("NFC: активный считыватель '{}'.", reader_name);
            match self.monitor_reader(
                app_handle,
                context,
                &reader_name,
                last_reader_state_json,
                last_card_status_json,
            )? {
                MonitorControl::Rescan => continue,
            }
        }
    }

    fn monitor_reader(
        &self,
        app_handle: &AppHandle,
        context: &Context,
        reader_name: &str,
        last_reader_state_json: &mut String,
        last_card_status_json: &mut String,
    ) -> Result<MonitorControl, Error> {
        info!("NFC: мониторинг карты запущен для '{}'.", reader_name);
        let mut states = vec![
            ReaderState::new(pcsc::PNP_NOTIFICATION().to_owned(), State::UNAWARE),
            ReaderState::new(
                CString::new(reader_name).expect("reader name should not contain nul"),
                State::UNAWARE,
            ),
        ];
        prime_reader_states(context, &mut states)?;

        match self.emit_card_probe(
            app_handle,
            context,
            reader_name,
            last_reader_state_json,
            last_card_status_json,
        )? {
            ProbeControl::Continue => {}
            ProbeControl::Rescan => return Ok(MonitorControl::Rescan),
        }

        loop {
            match context.get_status_change(Some(STATUS_CHANGE_TIMEOUT), &mut states) {
                Ok(()) => {
                    let topology_changed = states[0].event_state().contains(State::CHANGED);
                    let reader_event_state = states[1].event_state();

                    if topology_changed {
                        info!("NFC: обнаружено изменение топологии считывателей.");
                        let readers = nfc_handler::list_readers_internal(context)?;
                        if !readers.iter().any(|name| name == reader_name) {
                            warn!("NFC: считыватель '{}' больше недоступен.", reader_name);
                            self.emit_reader_state(
                                app_handle,
                                last_reader_state_json,
                                ReaderStatePayload::disconnected(
                                    Some(reader_name.to_string()),
                                    "Считыватель отключен. Ожидаем повторное подключение.",
                                ),
                            );
                            self.emit_card_status(
                                app_handle,
                                last_card_status_json,
                                CardStatusPayload {
                                    uid: None,
                                    error: Some(READER_UNAVAILABLE_MESSAGE.to_string()),
                                },
                            );
                            return Ok(MonitorControl::Rescan);
                        }
                    }

                    if reader_event_state.intersects(State::UNKNOWN | State::UNAVAILABLE) {
                        warn!(
                            "NFC: считыватель '{}' перешел в состояние unavailable/unknown.",
                            reader_name
                        );
                        self.emit_reader_state(
                            app_handle,
                            last_reader_state_json,
                            ReaderStatePayload::disconnected(
                                Some(reader_name.to_string()),
                                "Считыватель недоступен. Ожидаем восстановление.",
                            ),
                        );
                        self.emit_card_status(
                            app_handle,
                            last_card_status_json,
                            CardStatusPayload {
                                uid: None,
                                error: Some(READER_UNAVAILABLE_MESSAGE.to_string()),
                            },
                        );
                        return Ok(MonitorControl::Rescan);
                    }

                    if topology_changed || reader_event_state.contains(State::CHANGED) {
                        match self.emit_card_probe(
                            app_handle,
                            context,
                            reader_name,
                            last_reader_state_json,
                            last_card_status_json,
                        )? {
                            ProbeControl::Continue => {}
                            ProbeControl::Rescan => return Ok(MonitorControl::Rescan),
                        }
                    }

                    for state in &mut states {
                        state.sync_current_state();
                    }
                }
                Err(Error::Timeout) => {
                    context.is_valid()?;
                }
                Err(err) => return Err(err),
            }
        }
    }

    fn emit_card_probe(
        &self,
        app_handle: &AppHandle,
        context: &Context,
        reader_name: &str,
        last_reader_state_json: &mut String,
        last_card_status_json: &mut String,
    ) -> Result<ProbeControl, Error> {
        match nfc_handler::get_card_uid_internal(context, reader_name) {
            Ok(uid_bytes) => {
                self.emit_reader_state(
                    app_handle,
                    last_reader_state_json,
                    ReaderStatePayload::card_present(reader_name.to_string()),
                );
                self.emit_card_status(
                    app_handle,
                    last_card_status_json,
                    CardStatusPayload {
                        uid: Some(hex::encode(uid_bytes)),
                        error: None,
                    },
                );
                Ok(ProbeControl::Continue)
            }
            Err(Error::NoSmartcard) | Err(Error::RemovedCard) => {
                self.emit_reader_state(
                    app_handle,
                    last_reader_state_json,
                    ReaderStatePayload::ready(reader_name.to_string()),
                );
                self.emit_card_status(
                    app_handle,
                    last_card_status_json,
                    CardStatusPayload {
                        uid: None,
                        error: None,
                    },
                );
                Ok(ProbeControl::Continue)
            }
            Err(err) if is_reader_missing_error(&err) => {
                warn!(
                    "NFC: потерян доступ к считывателю '{}': {}. Переходим к повторному поиску.",
                    reader_name, err
                );
                self.emit_reader_state(
                    app_handle,
                    last_reader_state_json,
                    ReaderStatePayload::disconnected(
                        Some(reader_name.to_string()),
                        "Считыватель отключен. Идет повторное обнаружение.",
                    ),
                );
                self.emit_card_status(
                    app_handle,
                    last_card_status_json,
                    CardStatusPayload {
                        uid: None,
                        error: Some(READER_UNAVAILABLE_MESSAGE.to_string()),
                    },
                );
                Ok(ProbeControl::Rescan)
            }
            Err(err) => Err(err),
        }
    }

    fn wait_for_topology_change(&self, context: &Context) -> Result<bool, Error> {
        let mut states = vec![ReaderState::new(
            pcsc::PNP_NOTIFICATION().to_owned(),
            State::UNAWARE,
        )];
        prime_reader_states(context, &mut states)?;

        match context.get_status_change(Some(STATUS_CHANGE_TIMEOUT), &mut states) {
            Ok(()) => Ok(states[0].event_state().contains(State::CHANGED)),
            Err(Error::Timeout) => Ok(false),
            Err(err) => Err(err),
        }
    }

    fn handle_runtime_error(
        &self,
        app_handle: &AppHandle,
        last_reader_state_json: &mut String,
        last_card_status_json: &mut String,
        err: Error,
    ) {
        self.store_command_context(None);

        if is_recoverable_runtime_error(&err) {
            warn!("NFC: требуется восстановление контекста PC/SC: {}", err);
            self.emit_reader_state(
                app_handle,
                last_reader_state_json,
                ReaderStatePayload::recovering(
                    None,
                    format!("Контекст PC/SC будет пересоздан: {}", err),
                ),
            );
            self.emit_card_status(
                app_handle,
                last_card_status_json,
                CardStatusPayload {
                    uid: None,
                    error: Some(READER_RECOVERING_MESSAGE.to_string()),
                },
            );
            return;
        }

        error!("NFC: непредвиденная ошибка runtime: {}", err);
        self.emit_reader_state(
            app_handle,
            last_reader_state_json,
            ReaderStatePayload::error(None, format!("Ошибка NFC runtime: {}", err)),
        );
        self.emit_card_status(
            app_handle,
            last_card_status_json,
            CardStatusPayload {
                uid: None,
                error: Some(format!("Ошибка NFC runtime: {}", err)),
            },
        );
    }

    fn emit_reader_state(
        &self,
        app_handle: &AppHandle,
        last_payload_json: &mut String,
        payload: ReaderStatePayload,
    ) {
        *self.latest_reader_state.lock().unwrap() = payload.clone();
        let now = Instant::now();
        {
            let last_emitted = self.last_emitted_reader_state.lock().unwrap();
            if !should_emit_reader_state(last_emitted.as_ref(), &payload, now) {
                return;
            }
        }
        match serde_json::to_string(&payload) {
            Ok(current_payload_json) if current_payload_json != *last_payload_json => {
                if let Err(err) = app_handle.emit(READER_STATE_CHANGED_EVENT, payload.clone()) {
                    error!("NFC: не удалось отправить reader-state-changed: {}", err);
                    return;
                }
                let mut last_emitted = self.last_emitted_reader_state.lock().unwrap();
                *last_emitted = Some(EmittedReaderState {
                    payload: payload.clone(),
                    emitted_at: now,
                });
                *last_payload_json = current_payload_json;
            }
            Ok(_) => {}
            Err(err) => error!("NFC: не удалось сериализовать reader state: {}", err),
        }
    }

    fn emit_card_status(
        &self,
        app_handle: &AppHandle,
        last_payload_json: &mut String,
        payload: CardStatusPayload,
    ) {
        match serde_json::to_string(&payload) {
            Ok(current_payload_json) if current_payload_json != *last_payload_json => {
                if let Err(err) = app_handle.emit(CARD_STATUS_CHANGED_EVENT, payload) {
                    error!("NFC: не удалось отправить card-status-changed: {}", err);
                    return;
                }
                *last_payload_json = current_payload_json;
            }
            Ok(_) => {}
            Err(err) => error!("NFC: не удалось сериализовать card status: {}", err),
        }
    }

    fn store_command_context(&self, context: Option<Context>) {
        let mut slot = self.command_context.lock().unwrap();
        *slot = context;
    }
}

fn choose_reader_name(readers: &[String], preferred_reader_name: Option<&str>) -> String {
    if let Some(preferred_reader_name) = preferred_reader_name {
        if readers
            .iter()
            .any(|reader_name| reader_name == preferred_reader_name)
        {
            return preferred_reader_name.to_string();
        }
    }

    readers
        .first()
        .cloned()
        .expect("choose_reader_name called with empty list")
}

fn next_backoff(current: Duration) -> Duration {
    let next = current.saturating_mul(2);
    next.min(MAX_RECOVERY_BACKOFF)
}

fn prime_reader_states(context: &Context, states: &mut [ReaderState]) -> Result<(), Error> {
    match context.get_status_change(Some(Duration::from_millis(0)), states) {
        Ok(()) | Err(Error::Timeout) => {
            for state in states {
                state.sync_current_state();
            }
            Ok(())
        }
        Err(err) => Err(err),
    }
}

fn is_reader_missing_error(err: &Error) -> bool {
    matches!(
        err,
        Error::UnknownReader | Error::ReaderUnavailable | Error::NoReadersAvailable
    )
}

fn is_recoverable_runtime_error(err: &Error) -> bool {
    matches!(
        err,
        Error::InvalidHandle
            | Error::NoService
            | Error::ServiceStopped
            | Error::ReaderUnavailable
            | Error::UnknownReader
            | Error::NoReadersAvailable
            | Error::CommError
            | Error::Shutdown
            | Error::InternalError
            | Error::UnknownError
    )
}

fn should_emit_reader_state(
    last_emitted: Option<&EmittedReaderState>,
    payload: &ReaderStatePayload,
    now: Instant,
) -> bool {
    let Some(last_emitted) = last_emitted else {
        return true;
    };

    if last_emitted.payload == *payload {
        return false;
    }

    if payload.state == ReaderLifecycleState::Scanning
        && matches!(
            last_emitted.payload.state,
            ReaderLifecycleState::Disconnected | ReaderLifecycleState::Recovering
        )
        && now.duration_since(last_emitted.emitted_at) < MIN_SCANNING_REEMIT_DELAY
    {
        return false;
    }

    true
}

#[cfg(test)]
mod tests {
    use super::{
        choose_reader_name, next_backoff, should_emit_reader_state, EmittedReaderState,
        ReaderStatePayload, MAX_RECOVERY_BACKOFF, MIN_SCANNING_REEMIT_DELAY,
    };
    use std::time::{Duration, Instant};

    #[test]
    fn choose_reader_keeps_preferred_reader_when_it_still_exists() {
        let readers = vec!["Reader A".to_string(), "Reader B".to_string()];
        assert_eq!(choose_reader_name(&readers, Some("Reader B")), "Reader B");
    }

    #[test]
    fn choose_reader_falls_back_to_first_available_reader() {
        let readers = vec!["Reader A".to_string(), "Reader B".to_string()];
        assert_eq!(choose_reader_name(&readers, Some("Reader C")), "Reader A");
    }

    #[test]
    fn backoff_is_bounded() {
        assert_eq!(
            next_backoff(Duration::from_millis(500)),
            Duration::from_secs(1)
        );
        assert_eq!(next_backoff(MAX_RECOVERY_BACKOFF), MAX_RECOVERY_BACKOFF);
    }

    #[test]
    fn duplicate_reader_state_is_not_emitted() {
        let payload = ReaderStatePayload::disconnected(None, "reader unavailable");
        let last_emitted = EmittedReaderState {
            payload: payload.clone(),
            emitted_at: Instant::now(),
        };

        assert!(!should_emit_reader_state(
            Some(&last_emitted),
            &payload,
            Instant::now()
        ));
    }

    #[test]
    fn scanning_is_debounced_after_disconnect() {
        let payload = ReaderStatePayload::scanning("rescanning");
        let last_emitted = EmittedReaderState {
            payload: ReaderStatePayload::disconnected(None, "reader unavailable"),
            emitted_at: Instant::now(),
        };

        assert!(!should_emit_reader_state(
            Some(&last_emitted),
            &payload,
            Instant::now()
        ));
    }

    #[test]
    fn scanning_is_allowed_after_cooldown() {
        let payload = ReaderStatePayload::scanning("rescanning");
        let last_emitted = EmittedReaderState {
            payload: ReaderStatePayload::recovering(None, "recovering"),
            emitted_at: Instant::now() - MIN_SCANNING_REEMIT_DELAY - Duration::from_millis(1),
        };

        assert!(should_emit_reader_state(
            Some(&last_emitted),
            &payload,
            Instant::now()
        ));
    }

    #[test]
    fn same_lifecycle_with_different_payload_is_emitted() {
        let payload =
            ReaderStatePayload::disconnected(Some("Reader A".to_string()), "reader unplugged");
        let last_emitted = EmittedReaderState {
            payload: ReaderStatePayload::disconnected(None, "reader not found"),
            emitted_at: Instant::now(),
        };

        assert!(should_emit_reader_state(
            Some(&last_emitted),
            &payload,
            Instant::now()
        ));
    }
}
