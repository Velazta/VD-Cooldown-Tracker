# Violence District Cooldown Tracker

Companion application eksternal berbasis Computer Vision untuk mengamati game *Violence District* (Roblox) secara pasif dan menampilkan timer cooldown kemampuan (*The Hidden → Leap*) melalui transparent overlay.

## 1. Safety & Platform Policy
Aplikasi ini beroperasi 100% secara eksternal melalui pengamatan visual layar (screen capture).
- **TIDAK** melakukan memory reading, injection, hooking, atau modifikasi client Roblox.
- **TIDAK** menggunakan Roblox executor atau exploit API.
- **TIDAK** melakukan otomasi gameplay atau macro input.

## 2. Lingkungan Pengembangan (Prerequisites)
- **OS:** Windows 10 / 11 64-bit
- **Python:** 3.13 / 3.14 (64-bit)
- **Primary Stack:** PySide6, OpenCV, NumPy, MSS

## 3. Instalasi & Setup

1. **Clone repository & buat Virtual Environment:**
   ```powershell
   git clone <repo-url>
   cd OverlayToolsVD
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install mss bettercam pywin32
   ```

3. **Verifikasi Lingkungan (Smoke Test):**
   ```powershell
   python main.py
   ```

4. **Menjalankan Screen Capture Spike:**
   ```powershell
   python tests/spike_capture_benchmark.py
   ```
