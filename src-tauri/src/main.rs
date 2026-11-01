// Prevents an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    fs,
    path::PathBuf,
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use serde::{Deserialize, Serialize};
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, PhysicalPosition, State, WebviewWindow, WindowEvent,
};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};

// ---------------------------------------------------------------------------
// Config (persisted as JSON in the per-user app config dir)
// ---------------------------------------------------------------------------

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(default)]
struct Config {
    name: String,
    character: String,
    interval_min: u64,
    snooze_min: u64,
    autostart: bool,
    corner: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            name: String::new(),
            character: "me".into(),
            interval_min: 45,
            snooze_min: 10,
            autostart: false,
            corner: "bottom-right".into(),
        }
    }
}

impl Config {
    fn sanitized(mut self) -> Self {
        self.interval_min = self.interval_min.clamp(1, 24 * 60);
        self.snooze_min = self.snooze_min.clamp(1, 24 * 60);
        self.name = self.name.trim().chars().take(30).collect();
        if !["bottom-right", "bottom-left", "top-right", "top-left"].contains(&self.corner.as_str()) {
            self.corner = "bottom-right".into();
        }
        self
    }
}

#[derive(Serialize)]
struct Status {
    seconds_left: u64,
    waiting_for_answer: bool,
}

// ---------------------------------------------------------------------------
// Scheduler state
// ---------------------------------------------------------------------------

struct Sched {
    /// When the next reminder fires. `None` while the buddy is on screen.
    next_at: Option<Instant>,
    /// True while the buddy window is visible and waiting for Yes / Later.
    waiting: bool,
    shown_at: Option<Instant>,
}

struct AppState {
    config: Mutex<Config>,
    sched: Mutex<Sched>,
    config_path: PathBuf,
}

/// If the user ignores the buddy this long, treat it as "Later".
const AUTO_SNOOZE_AFTER: Duration = Duration::from_secs(20 * 60);
const MARGIN_PX: f64 = 14.0;

fn load_config(path: &PathBuf) -> Config {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str::<Config>(&s).ok())
        .unwrap_or_default()
        .sanitized()
}

fn write_config(path: &PathBuf, cfg: &Config) {
    if let Some(dir) = path.parent() {
        let _ = fs::create_dir_all(dir);
    }
    if let Ok(json) = serde_json::to_string_pretty(cfg) {
        let _ = fs::write(path, json);
    }
}

// ---------------------------------------------------------------------------
// Buddy window helpers
// ---------------------------------------------------------------------------

fn buddy_window(app: &AppHandle) -> Option<WebviewWindow> {
    app.get_webview_window("buddy")
}

fn position_buddy(app: &AppHandle, corner: &str) {
    let Some(win) = buddy_window(app) else { return };
    let Ok(Some(monitor)) = app.primary_monitor() else { return };
    let Ok(size) = win.outer_size() else { return };

    let area = monitor.work_area();
    let scale = monitor.scale_factor();
    let margin = (MARGIN_PX * scale) as i32;

    let (w, h) = (size.width as i32, size.height as i32);
    let (ax, ay) = (area.position.x, area.position.y);
    let (aw, ah) = (area.size.width as i32, area.size.height as i32);

    let x = if corner.ends_with("left") { ax + margin } else { ax + aw - w - margin };
    let y = if corner.starts_with("top") { ay + margin } else { ay + ah - h - margin };

    let _ = win.set_position(PhysicalPosition::new(x, y));
}

fn show_buddy(app: &AppHandle) {
    let state = app.state::<AppState>();
    let corner = state.config.lock().unwrap().corner.clone();
    position_buddy(app, &corner);
    if let Some(win) = buddy_window(app) {
        let _ = win.set_always_on_top(true);
        let _ = win.show();
    }
    let _ = app.emit_to("buddy", "remind", ());
}

fn hide_buddy(app: &AppHandle) {
    if let Some(win) = buddy_window(app) {
        let _ = win.hide();
    }
}

fn show_settings(app: &AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
    }
}

fn schedule_in(state: &AppState, minutes: u64) {
    let mut s = state.sched.lock().unwrap();
    s.waiting = false;
    s.shown_at = None;
    s.next_at = Some(Instant::now() + Duration::from_secs(minutes * 60));
}

fn apply_autostart(app: &AppHandle, enabled: bool) {
    let launcher = app.autolaunch();
    let _ = if enabled { launcher.enable() } else { launcher.disable() };
}

// ---------------------------------------------------------------------------
// Commands (called from the Vue frontend)
// ---------------------------------------------------------------------------

#[tauri::command]
fn get_config(state: State<AppState>) -> Config {
    state.config.lock().unwrap().clone()
}

#[tauri::command]
fn save_config(app: AppHandle, state: State<AppState>, config: Config) {
    let config = config.sanitized();
    let (interval_changed, corner) = {
        let mut cur = state.config.lock().unwrap();
        let changed = cur.interval_min != config.interval_min;
        *cur = config.clone();
        (changed, config.corner.clone())
    };
    write_config(&state.config_path, &config);
    apply_autostart(&app, config.autostart);

    let waiting = state.sched.lock().unwrap().waiting;
    if waiting {
        position_buddy(&app, &corner);
    } else if interval_changed {
        schedule_in(&state, config.interval_min);
    }
}

#[tauri::command]
fn get_status(state: State<AppState>) -> Status {
    let s = state.sched.lock().unwrap();
    let seconds_left = s
        .next_at
        .map(|t| t.saturating_duration_since(Instant::now()).as_secs())
        .unwrap_or(0);
    Status { seconds_left, waiting_for_answer: s.waiting }
}

#[tauri::command]
fn remind_now(state: State<AppState>) {
    let mut s = state.sched.lock().unwrap();
    if !s.waiting {
        s.next_at = Some(Instant::now());
    }
}

#[tauri::command]
fn answer_done(app: AppHandle, state: State<AppState>) {
    hide_buddy(&app);
    let mins = state.config.lock().unwrap().interval_min;
    schedule_in(&state, mins);
}

#[tauri::command]
fn answer_later(app: AppHandle, state: State<AppState>) {
    hide_buddy(&app);
    let mins = state.config.lock().unwrap().snooze_min;
    schedule_in(&state, mins);
}

// ---------------------------------------------------------------------------
// Background ticker: fires reminders and auto-snoozes ignored ones
// ---------------------------------------------------------------------------

fn start_ticker(app: AppHandle) {
    thread::spawn(move || loop {
        thread::sleep(Duration::from_secs(1));
        let state = app.state::<AppState>();
        let now = Instant::now();

        let (fire, auto_snooze) = {
            let mut s = state.sched.lock().unwrap();
            let fire = matches!(s.next_at, Some(t) if now >= t) && !s.waiting;
            if fire {
                s.next_at = None;
                s.waiting = true;
                s.shown_at = Some(now);
            }
            let auto = s.waiting
                && s.shown_at.map(|t| now.duration_since(t) >= AUTO_SNOOZE_AFTER).unwrap_or(false);
            (fire, auto)
        };

        if fire {
            show_buddy(&app);
        }
        if auto_snooze {
            hide_buddy(&app);
            let mins = state.config.lock().unwrap().snooze_min;
            schedule_in(&state, mins);
        }
    });
}

// ---------------------------------------------------------------------------
// App bootstrap
// ---------------------------------------------------------------------------

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, None))
        .invoke_handler(tauri::generate_handler![
            get_config,
            save_config,
            get_status,
            remind_now,
            answer_done,
            answer_later
        ])
        .setup(|app| {
            // --- state ---
            let config_path = app
                .path()
                .app_config_dir()
                .map(|d| d.join("config.json"))
                .unwrap_or_else(|_| PathBuf::from("config.json"));
            let config = load_config(&config_path);
            let first_in = config.interval_min;
            apply_autostart(app.handle(), config.autostart);

            app.manage(AppState {
                config: Mutex::new(config),
                sched: Mutex::new(Sched {
                    next_at: Some(Instant::now() + Duration::from_secs(first_in * 60)),
                    waiting: false,
                    shown_at: None,
                }),
                config_path,
            });

            // --- tray ---
            let settings_i = MenuItem::with_id(app, "settings", "Open settings", true, None::<&str>)?;
            let now_i = MenuItem::with_id(app, "now", "Remind me now", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&settings_i, &now_i, &quit_i])?;

            TrayIconBuilder::with_id("tray")
                .icon(app.default_window_icon().cloned().expect("app icon"))
                .tooltip("Reminder Buddy")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "settings" => show_settings(app),
                    "now" => {
                        let state = app.state::<AppState>();
                        let mut s = state.sched.lock().unwrap();
                        if !s.waiting {
                            s.next_at = Some(Instant::now());
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_settings(tray.app_handle());
                    }
                })
                .build(app)?;

            start_ticker(app.handle().clone());
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the settings window just hides it; the app lives in the tray.
            if let WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Reminder Buddy");
}
