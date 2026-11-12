"""
Application Settings & Runtime Configuration Manager
Violence District Cooldown Tracker — Day 6 (Poin 6.3)
"""
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional

from processing.roi_processor import ROIConfig
from app.logger import get_logger

logger = get_logger("settings")


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
    x: int = 100
    y: int = 100
    width: int = 220
    height: int = 220
    opacity: float = 0.95
    visible: bool = True
    always_on_top: bool = True
    click_through: bool = True
    fps_display: bool = True
    position: Dict[str, int] = field(default_factory=lambda: {"x": 100, "y": 100})

    def to_dict(self) -> Dict[str, Any]:
        """Serialisasi model OverlaySettings ke dictionary terstruktur."""
        return {
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
            "opacity": round(float(self.opacity), 2),
            "visible": bool(self.visible),
            "always_on_top": bool(self.always_on_top),
            "click_through": bool(self.click_through),
            "fps_display": bool(self.fps_display),
            "position": {"x": int(self.x), "y": int(self.y)},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OverlaySettings":
        """Membuat instance OverlaySettings dari dictionary dengan validasi dan batas aman."""
        if not isinstance(data, dict):
            return cls()

        pos = data.get("position", {})
        if not isinstance(pos, dict):
            pos = {}

        # Mendukung koordinat flat (x, y) dan struktur position dict ({"x": ..., "y": ...})
        x_val = data.get("x", pos.get("x", 100))
        y_val = data.get("y", pos.get("y", 100))
        width_val = data.get("width", 220)
        height_val = data.get("height", 220)
        opacity_val = data.get("opacity", 0.95)
        visible_val = data.get("visible", True)
        always_on_top_val = data.get("always_on_top", True)
        click_through_val = data.get("click_through", True)
        fps_display_val = data.get("fps_display", True)

        try:
            x_int = max(0, int(x_val))
            y_int = max(0, int(y_val))
        except (ValueError, TypeError):
            x_int, y_int = 100, 100

        try:
            w_int = max(60, min(1920, int(width_val)))
            h_int = max(60, min(1080, int(height_val)))
        except (ValueError, TypeError):
            w_int, h_int = 220, 220

        try:
            op_flt = max(0.2, min(1.0, float(opacity_val)))
        except (ValueError, TypeError):
            op_flt = 0.95

        return cls(
            x=x_int,
            y=y_int,
            width=w_int,
            height=h_int,
            opacity=op_flt,
            visible=bool(visible_val),
            always_on_top=bool(always_on_top_val),
            click_through=bool(click_through_val),
            fps_display=bool(fps_display_val),
            position={"x": x_int, "y": y_int},
        )


@dataclass
class AppConfig:
    schema_version: int = 1
    app: AppInfo = field(default_factory=AppInfo)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    active_killer_id: str = "the_hidden"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Pastikan ROIConfig dan OverlaySettings terserialisasi dengan benar
        d["capture"]["roi"] = self.capture.roi.to_dict()
        d["overlay"] = self.overlay.to_dict()
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
        overlay_settings = OverlaySettings.from_dict(ovl_raw)

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
            logger.info("Configuration file not found at %s. Creating default.", target_path)
            self._config = AppConfig()
            self.save(self._config, target_path)
            return self._config

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self._config = AppConfig.from_dict(raw_data)
            logger.info("Successfully loaded application config from %s", target_path)
        except Exception as exc:
            # Fallback aman jika JSON corrupt
            logger.warning("Failed to parse config at %s (%s). Falling back to defaults.", target_path, exc)
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
        logger.info("Saved application config to %s", target_path)
