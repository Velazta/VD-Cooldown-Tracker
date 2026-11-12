"""
Application Settings & Runtime Configuration Manager
Violence District Cooldown Tracker — Day 6 (Poin 6.3)
"""
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional

from processing.roi_processor import ROIConfig


@dataclass
class AppInfo:
    name: str = "Violence District Cooldown Tracker"
    version: str = "0.1.0-alpha"
    debug_mode: bool = True


@dataclass
class CaptureSettings:
    target_title: str = "Roblox"
    backend: str = "windows_capture"
    target_fps: int = 30
    roi: ROIConfig = field(default_factory=lambda: ROIConfig(x=320, y=150, width=1280, height=780, enabled=True))


@dataclass
class OverlaySettings:
    always_on_top: bool = True
    click_through: bool = True
    opacity: float = 0.9
    fps_display: bool = True
    position: Dict[str, int] = field(default_factory=lambda: {"x": 100, "y": 100})


@dataclass
class AppConfig:
    schema_version: int = 1
    app: AppInfo = field(default_factory=AppInfo)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    active_killer_id: str = "the_hidden"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Pastikan ROIConfig terserialisasi dengan benar
        d["capture"]["roi"] = self.capture.roi.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Membuat instance AppConfig dari dictionary dengan fallback nilai default yang aman."""
        if not isinstance(data, dict):
            return cls()

        app_raw = data.get("app", {})
        app_info = AppInfo(
            name=str(app_raw.get("name", "Violence District Cooldown Tracker")),
            version=str(app_raw.get("version", "0.1.0-alpha")),
            debug_mode=bool(app_raw.get("debug_mode", True))
        )

        cap_raw = data.get("capture", {})
        roi_raw = cap_raw.get("roi", {})
        roi_config = ROIConfig.from_dict(roi_raw)

        capture_settings = CaptureSettings(
            target_title=str(cap_raw.get("target_title", "Roblox")),
            backend=str(cap_raw.get("backend", "windows_capture")),
            target_fps=int(cap_raw.get("target_fps", 30)),
            roi=roi_config
        )

        ovl_raw = data.get("overlay", {})
        overlay_settings = OverlaySettings(
            always_on_top=bool(ovl_raw.get("always_on_top", True)),
            click_through=bool(ovl_raw.get("click_through", True)),
            opacity=float(ovl_raw.get("opacity", 0.9)),
            fps_display=bool(ovl_raw.get("fps_display", True)),
            position=dict(ovl_raw.get("position", {"x": 100, "y": 100}))
        )

        return cls(
            schema_version=int(data.get("schema_version", 1)),
            app=app_info,
            capture=capture_settings,
            overlay=overlay_settings,
            active_killer_id=str(data.get("active_killer_id", "the_hidden"))
        )


class SettingsManager:
    """
    Manajer konfigurasi runtime aplikasi.
    Menyediakan fallback otomatis ke nilai default jika konfigurasi parsial atau hilang.
    """

    DEFAULT_PATH = Path("config/app_config.json")

    def __init__(self, config_path: Optional[Path] = None):
        self.path = config_path or self.DEFAULT_PATH
        self._config: Optional[AppConfig] = None

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self.load()
        return self._config

    def load(self, path: Optional[Path] = None) -> AppConfig:
        target_path = path or self.path
        if not target_path.exists():
            # Jika file belum ada, gunakan konfigurasi default dan simpan
            self._config = AppConfig()
            self.save(self._config, target_path)
            return self._config

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self._config = AppConfig.from_dict(raw_data)
        except Exception:
            # Fallback aman jika JSON corrupt
            self._config = AppConfig()

        self.path = target_path
        return self._config

    def save(self, config: Optional[AppConfig] = None, path: Optional[Path] = None) -> None:
        target_config = config or self._config or AppConfig()
        target_path = path or self.path

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(target_config.to_dict(), f, indent=2, ensure_ascii=False)
        self._config = target_config
