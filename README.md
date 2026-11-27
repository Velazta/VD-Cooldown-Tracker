<p align="center">
  <img src="OVERLAY%20UI/CARD%20PICK%20SYSTEM/HIDDEN%20CARD.png" width="120" alt="Violence District Cooldown Tracker emblem">
</p>

<h1 align="center">Violence District Cooldown Tracker</h1>

<p align="center">
  <b>External desktop cooldown overlay &amp; tactical companion for Roblox <i>Violence District</i>.</b><br>
  Animated pop-up ability banners, OS-level multi-trigger keyboard &amp; mouse hotkeys, in-game killer<br>
  card picker carousel, and a modular local Computer Vision pipeline — all in a transparent click-through HUD.
</p>

<p align="center">
  <img alt="Python 3.13 / 3.14" src="https://img.shields.io/badge/Python-3.13%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="PySide6" src="https://img.shields.io/badge/PySide6-Qt6%20Overlay-41CD52?style=flat-square&logo=qt&logoColor=white">
  <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-4.10+-5C3EE8?style=flat-square&logo=opencv&logoColor=white">
  <img alt="ONNX Runtime" src="https://img.shields.io/badge/ONNX_Runtime-1.20+-005CED?style=flat-square&logo=onnx&logoColor=white">
  <img alt="Platform: Windows x64" src="https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-0078D6?style=flat-square&logo=windows&logoColor=white">
</p>

<p align="center">
  <a href="#a-look-around">A look around</a> ·
  <a href="#features">Features</a> ·
  <a href="#supported-killers">Supported Killers</a> ·
  <a href="#tech-stack">Tech Stack</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#safety--platform-policy">Safety &amp; Policy</a>
</p>

<br>

<p align="center">
  <img src="OVERLAY%20UI/CARD%20PICK%20SYSTEM/CONTOH%20FRAME%20INGAME.png" alt="Violence District Cooldown Tracker in-game preview showing the top killer card picker carousel and left-edge pop-up cooldown banner during gameplay" width="100%">
  <br><sub><b>Live In-Game Overlay</b>: top Card Picker Carousel for instant killer switching and smooth left-edge Pop-Up Cooldown Banners without Alt-Tabbing.</sub>
</p>

<br>

> [!NOTE]
> **100% external &amp; non-invasive companion.** All capture, hotkey listening, cooldown timing, and
> transparent HUD rendering run completely outside the Roblox client using passive screen observation
> and standard Windows APIs — zero memory reading, zero injection, and zero automated gameplay macros.

<br>

<table>
  <tr>
    <td width="25%" valign="top">
      <h3>⚡ Animated Pop-Up HUD</h3>
      Stylized killer ability banners slide smoothly from the left edge with easing animations, crisp digital countdown timers, and full click-through transparency.
    </td>
    <td width="25%" valign="top">
      <h3>🎮 Multi-Trigger Hotkeys</h3>
      Low-level Win32 pass-through hooks supporting simultaneous keyboard &amp; side mouse buttons (e.g. <code>[, Mouse4</code>, <code>], Mouse5</code>) without blocking game inputs.
    </td>
    <td width="25%" valign="top">
      <h3>🃏 In-Game Card Picker</h3>
      Summon a sleek transparent killer selection carousel directly over your game screen, browse with arrow keys or mouse, and switch cooldown profiles mid-match.
    </td>
    <td width="25%" valign="top">
      <h3>👁️ Local CV &amp; Audio Pipeline</h3>
      Modular screen capture (<code>mss</code>), ROI cropping, OpenCV preprocessing, motion/template matching, audio surge hooks, and ONNX Runtime inference ready.
    </td>
  </tr>
</table>

<br>

## A look around

<table>
<tr>
<td width="50%" valign="top">
  <img src="OVERLAY%20UI/example_countdown_time.png" alt="Stylized Killer Ability Cooldown Banner showing Evil Grasp 30s countdown layout" width="100%">
  <p align="center"><sub><b>Pop-Up Ability Banner</b>: custom per-killer artwork paired with high-contrast digital countdown timers</sub></p>
</td>
<td width="50%" valign="top">
  <img src="OVERLAY%20UI/CONTOH%20FRAME%20INGAME.png" alt="In-game gameplay view with The Butcher Chain 30s cooldown banner overlaid on the left edge" width="100%">
  <p align="center"><sub><b>Click-Through Gameplay Integration</b>: stays always-on-top over Roblox without stealing focus or mouse clicks</sub></p>
</td>
</tr>
</table>

## Features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>OS-Level Global Hotkeys &amp; Presets</h3>
      Powered by native Win32 <code>WH_KEYBOARD_LL</code> and <code>WH_MOUSE_LL</code> pass-through hooks via <code>ctypes</code>. Bind multiple alternative triggers per action using commas, slashes, or spaces (<code>[, Mouse4</code>), pick one-click presets (<b>Dual Mouse + [ ]</b>, <b>Mouse4/5</b>, <b>Bracket [ ]</b>, <b>Numpad</b>, <b>Laptop</b>), and toggle between Roblox-only focus or general Alt-Tab usage with smart chat-typing suppression.
    </td>
    <td width="50%" valign="top">
      <h3>Card Picker Carousel Overlay</h3>
      Press the Card Picker hotkey (default <code>=</code>) anytime during a match to bring up a floating killer selector carousel. Navigate smoothly across all configured killers using Left/Right arrows or mouse clicks and confirm immediately — updating active ability banks, banner assets, and cooldown durations in real time.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Monotonic Cooldown Engine</h3>
      Pure-Python <code>CooldownBank</code> and <code>CooldownManager</code> track per-ability state machines (<code>READY</code>, <code>WAITING_FOR_RELEASE</code>, <code>COOLDOWN</code>) using monotonic clock deadlines, duplicate-event suppression, configurable reaction offsets, repeat-restart options, and optional audio cues when abilities become ready.
    </td>
    <td width="50%" valign="top">
      <h3>JSON Killer &amp; Ability Database</h3>
      All killer metadata, ability names, trigger types (<code>on_cast_start</code> / <code>on_release</code>), and cooldown durations live in validated local configuration (<code>database/killerDatabase.json</code>) via <code>DatabaseManager</code> — making cooldown tuning or adding new killers straightforward without editing detection logic.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Screen Capture &amp; Experimental CV Pipeline</h3>
      Threaded <code>MSSWindowsCapture</code> with a drop-oldest <code>LatestFrameBuffer</code> (<code>maxlen=1</code>) feeds configurable ROI cropping, OpenCV preprocessing, and an asynchronous <code>DetectionWorker</code> combining template matching, optical/motion tracking, audio monitoring, and ONNX YOLOv8 inference — isolated cleanly from the Qt UI thread.
    </td>
    <td width="50%" valign="top">
      <h3>Persistent Settings &amp; Telemetry</h3>
      Automatically persists overlay coordinates, opacity, hotkeys, ROI bounds, and active killer selection to <code>config/app_config.json</code> with schema migration. Includes live process CPU/RAM and capture/processing FPS monitoring via <code>PerformanceMonitor</code>, plus Hall-of-Mirrors capture protection on the companion window.
    </td>
  </tr>
</table>

<br>

## Supported Killers

Configured out of the box in [`database/killerDatabase.json`](database/killerDatabase.json):

| Killer | Abilities | Cooldown (s) | Trigger Type |
|---|---|---|---|
| **The Hidden** | `Leap` · `Mark` | `25s` · `17s` | `on_cast_start` |
| **Veil** | `Through The Veil` | `40s` | `on_release` |
| **The Killer** | `Frenzy` | `24s` | `on_cast_start` |
| **The Stalker** | `Evil's Grasp` | `70s` | `on_cast_start` |
| **The Abysswalker** | `Dark Severance` · `Abyssal Burst` | `28s` · `26s` | `on_cast_start` |
| **The Masked** | `Mask Up (Durasi)` · `Mask Swap` | `90s` · `30s` | `on_cast_start` |
| **The Slasher** | `Lake Mist` · `Pursuit` | `30s` · `80s` | `on_cast_start` |
| **The Butcher** | `Your Heart Is Mine` · `Tendons (Steel Trap)` | `15s` · `45s` | `on_cast_start` |

<br>

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Desktop UI &amp; Overlay** | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6) | Main control panel, animated frameless pop-up banners, and click-through overlay window |
| **Screen Capture** | [MSS](https://python-mss.readthedocs.io/) &amp; Win32 API (`ctypes`) | Low-overhead screen capture, DWM window bounds, and global keyboard/mouse hooks |
| **Computer Vision** | [OpenCV](https://opencv.org/) &amp; [NumPy](https://numpy.org/) | ROI cropping, image preprocessing, template matching, and motion analysis |
| **ML Inference** | [ONNX Runtime](https://onnxruntime.ai/) | Lightweight local YOLOv8n inference without bundling full PyTorch runtime |
| **Telemetry &amp; Testing** | [psutil](https://github.com/giampaolo/psutil) &amp; [pytest](https://docs.pytest.org/) | CPU/RAM resource monitoring, latency benchmarking, and automated unit tests |
| **Packaging** | [PyInstaller](https://pyinstaller.org/) (`VDTracker.spec`) | Standalone portable Windows x64 `.exe` bundle with zero Python installation required |

<br>

## Quick Start

### Option A — Portable Windows App (No Setup Required)

1. Extract the portable release `.zip` (keep `VDTracker.exe`, `_internal/`, `config/`, `database/`, and `OVERLAY UI/` together in the same folder).
2. Double-click **`VDTracker.exe`**. *(If Windows SmartScreen appears, click **More info** → **Run anyway**.)*
3. Configure your preferred **Global Hotkeys** (e.g., `Preset Dual: Mouse + [ ]`) and launch *Violence District* in Roblox.

### Option B — Run from Source (Development)

**Prerequisites:** Windows 10 / 11 (64-bit) and Python 3.13 / 3.14 (64-bit).

1. **Clone the repository &amp; create a virtual environment:**
   ```powershell
   git clone https://github.com/Velazta/VD-Cooldown-Tracker.git
   cd VD-Cooldown-Tracker
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install mss bettercam pywin32
   ```

3. **Launch the application:**
   ```powershell
   python main.py
   ```

4. **Run tests:**
   ```powershell
   pytest
   ```

5. **Build standalone `.exe` (Optional):**
   ```powershell
   pip install pyinstaller
   pyinstaller VDTracker.spec --noconfirm
   ```
   Copy `database/killerDatabase.json` and `OVERLAY UI/` into `dist/VDTracker/` alongside `VDTracker.exe` if running outside `_internal`.

<br>

## Safety &amp; Platform Policy

This project is designed strictly as an external, passive companion tool:

- **Visible Screen Capture Only:** Observes rendered desktop output; never reads Roblox process memory or internal variables.
- **No Injection or Client Modification:** Zero DLL injection, API hooking, Roblox executors, exploit APIs, or client file patching.
- **No Gameplay Automation:** Hotkeys are pass-through listeners for manual timer tracking only — never sends automated inputs or macros.

<br>

## License and credits

<p align="center">
  <img src="OVERLAY%20UI/CARD%20PICK%20SYSTEM/HIDDEN%20CARD.png" alt="Violence District Cooldown Tracker" width="36"><br>
  <sub>Built by <a href="https://github.com/Velazta">Velazta</a> — external companion &amp; overlay tooling for <i>Violence District</i>.</sub>
</p>

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=Velazta/VD-Cooldown-Tracker&type=Date&legend=top-left)](https://www.star-history.com/?repos=Velazta%2FVD-Cooldown-Tracker&type=date&legend=top-left)
