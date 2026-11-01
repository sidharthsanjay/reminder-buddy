# Reminder Buddy 💧

A tiny animated desktop companion that nudges you to drink water. Lives in the
system tray, pops a character into a screen corner on a timer, and asks
**Yes, sip!** / **Later**.

Built with **Tauri 2 + Vue 3 + TypeScript + Rust**. Installer ≈ 5 MB.

---

## 1. Get the Windows installer (no tools needed on your PC)

The repo ships a GitHub Actions workflow that compiles the `.exe` for you.

1. Create a new repository on GitHub (private is fine).
2. Upload this whole folder to it — either `git push`, or drag-and-drop the
   files in the GitHub web UI (**Add file → Upload files**). Make sure the
   `.github/workflows/build-windows.yml` file is included.
3. Open the **Actions** tab → **Build Windows installer**. It starts
   automatically on the first push; you can also click **Run workflow**.
4. After ~5–8 minutes, open the finished run and download the
   **ReminderBuddy-windows** artifact. Unzip it → run
   `Reminder Buddy_0.1.0_x64-setup.exe` (NSIS) or the `.msi`.

   Windows SmartScreen may warn because the build is unsigned:
   **More info → Run anyway**.

Optional: push a tag like `v0.1.0` and the installers are also attached to a
GitHub **Release**.

## 2. Or build locally

```powershell
# prerequisites (one time)
winget install OpenJS.NodeJS.LTS
winget install Rustlang.Rustup        # then restart the terminal
# WebView2 is already part of Windows 10/11

npm install
npm run tauri dev       # run with hot reload
npm run tauri build     # installers land in src-tauri/target/release/bundle/
```

---

## 3. Custom characters

A character is a folder of PNGs. The build tool turns them into animated GIFs.

```
characters-src/
└── myhero/
    ├── manifest.json   (optional)
    ├── idle.png        ← REQUIRED
    ├── wave.png        ← shown when the reminder appears (optional)
    ├── happy.png       ← after "Yes"   (optional)
    └── sad.png         ← after "Later" (optional)
```

- PNG with **transparent background**, roughly square, any size (≈ 256–512 px is ideal).
- Any mood you don't supply is animated from `idle.png` instead.
- Want real frame-by-frame animation? Name frames `idle_01.png, idle_02.png, …`
  (same for `wave_`, `happy_`, `sad_`) and they're used as-is.

`manifest.json` (optional):

```json
{
  "name": "My Hero",
  "tagline": "The brave buddy",
  "greeting": "Yo {name}! 💧 Hydrate time?"
}
```

Then run:

```bash
python tools/make_character.py            # builds every folder in characters-src/
python tools/make_character.py myhero     # or just one
```

That writes `public/characters/myhero/*.gif` and updates
`public/characters/index.json`. Rebuild the app (push to GitHub, or
`npm run tauri build`) and the new buddy appears in the picker.

> Requires Python 3 + Pillow (`pip install pillow`).

The two built-in buddies (Droplet, Sprout) are drawn by
`tools/draw_placeholders.py`; delete their folders if you don't want them.

---

## 4. How it works

| Piece | File |
|---|---|
| Timer, tray menu, window positioning, config file | `src-tauri/src/main.rs` |
| Window definitions (settings + transparent buddy) | `src-tauri/tauri.conf.json` |
| Buddy popup (GIF + speech bubble + buttons) | `src/components/Buddy.vue` |
| Settings page | `src/components/Settings.vue` |
| Frontend ⇄ Rust calls, character loader | `src/api.ts` |
| Character GIFs shipped with the app | `public/characters/` |

Settings are saved to `%APPDATA%\com.next.reminderbuddy\config.json`.
Closing the settings window hides it; the app keeps running in the tray
(right-click the tray icon → **Quit** to exit). If a reminder is ignored for
20 minutes it is treated as "Later".
