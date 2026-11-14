# Environment Specifications

Dokumen catatan spesifikasi lingkungan eksekusi untuk **Violence District Cooldown Tracker** (Branch `feat/manual-detector`).

---

## 1. Spesifikasi Sistem & Perangkat Lunak

- **Operating System:** Windows 11 Pro 64-bit (`Windows-11-10.0.26300-SP0`)
- **Python Version:** Python 3.14.5 (tags/v3.14.5:5607950, 64-bit AMD64)
- **GUI Framework:** PySide6 version 6.12.0
- **Win32 API Bridge:** `ctypes` (Standard Python Library, zero external packages)
- **Monotonic Clock:** `time.monotonic()` (Zero-drift absolute hardware timing)
- **Target Game:** Roblox (*Violence District*)
- **Target Window Modes:** Windowed / Borderless Windowed (Display mode required for transparent always-on-top overlays)

---

## 2. Kebijakan Ketergantungan (Zero-New-Dependencies)

Sesuai aturan `AGENTS.md` dan `ANTIGRAVITY_PLAN_MANUAL_TRIGGER.md`:
- Pemicuan *Global Hotkey* diimplementasikan menggunakan Win32 `user32.RegisterHotKey` via modul standar `ctypes`.
- Penanganan event Win32 diintegrasikan secara native pada Qt Event Loop melalui `QAbstractNativeEventFilter`.
- Tidak ada penambahan paket pihak ketiga seperti `keyboard` atau `pynput` (menghindari hook tingkat rendah yang berpotensi memicu deteksi antivirus atau anti-cheat).
