"""Application Settings & Runtime Configuration Manager.

Violence District Cooldown Tracker — Day 6 / Manual Milestone (Phase M2)
Manages persistent settings in 'config/app_config.json' with automatic schema migration from v1 to v2.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from app.logger import get_logger
from processing.roi_processor import ROIConfig

logger = get_logger("settings")


@dataclass
class AppInfo:
    name: str = "Violence District Cooldown Tracker"
    version: str = "0.2.0-manual"
    debug_mode: bool = True


@dataclass
class CaptureSettings:
    target_title: str = "Roblox"
    backend: str = "windows_capture"
    target_fps: int = 30
    roi: ROIConfig = field(default_factory=lambda: ROIConfig(x=320, y=150, width=1280, height=780, enabled=True))
    enabled_on_start: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_title": str(self.target_title),
            "backend": str(self.backend),
            "target_fps": int(self.target_fps),
            "roi": self.roi.to_dict(),
            "enabled_on_start": bool(self.enabled_on_start),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaptureSettings":
        if not isinstance(data, dict):
            return cls()

        roi_raw = data.get("roi", {})
        roi_config = ROIConfig.from_dict(roi_raw)

        return cls(
            target_title=str(data.get("target_title", "Roblox")),
            backend=str(data.get("backend", "windows_capture")),
            target_fps=int(data.get("target_fps", 30)),
            roi=roi_config,
            enabled_on_start=bool(data.get("enabled_on_start", False)),
        )


@dataclass
class OverlaySettings:
    x: int = 24
    y: int = 280
    width: int = 360
    height: int = 360
    opacity: float = 0.95
    visible: bool = True
    always_on_top: bool = True
    click_through: bool = True
    fps_display: bool = True
    position: Dict[str, int] = field(default_factory=lambda: {"x": 24, "y": 280})

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
        x_val = data.get("x", pos.get("x", 24))
        y_val = data.get("y", pos.get("y", 280))
        width_val = data.get("width", 360)
        height_val = data.get("height", 360)
        opacity_val = data.get("opacity", 0.95)
        visible_val = data.get("visible", True)
        always_on_top_val = data.get("always_on_top", True)
        click_through_val = data.get("click_through", True)
        fps_display_val = data.get("fps_display", True)

        try:
            x_int = max(0, int(x_val))
            y_int = max(0, int(y_val))
        except (ValueError, TypeError):
            x_int, y_int = 24, 280

        try:
            w_int = max(60, min(1920, int(width_val)))
            h_int = max(60, min(1080, int(height_val)))
        except (ValueError, TypeError):
            w_int, h_int = 360, 360

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
class ManualSettings:
    """Konfigurasi khusus untuk mode companion manual trigger."""
    start_in_manual_mode: bool = True
    reaction_offset: float = 0.0          # 0.0 to 2.0s
    restart_on_repeat: bool = False       # Trigger saat cooldown aktif -> mulai ulang jika True
    sound_on_ready: bool = False          # Bunyi notifikasi saat cooldown selesai
    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        "trigger_ability_1": "Numpad1",
        "trigger_ability_2": "Numpad2",
        "trigger_ability_3": "Numpad3",
        "reset_all": "Numpad0",
        "toggle_overlay": "Numpad.",
        "toggle_card_picker": "=",
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_in_manual_mode": bool(self.start_in_manual_mode),
            "reaction_offset": round(float(self.reaction_offset), 2),
            "restart_on_repeat": bool(self.restart_on_repeat),
            "sound_on_ready": bool(self.sound_on_ready),
            "hotkeys": dict(self.hotkeys),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManualSettings":
        if not isinstance(data, dict):
            return cls()

        try:
            offset = max(0.0, min(2.0, float(data.get("reaction_offset", 0.0))))
        except (ValueError, TypeError):
            offset = 0.0

        default_hotkeys = {
            "trigger_ability_1": "Numpad1",
            "trigger_ability_2": "Numpad2",
            "trigger_ability_3": "Numpad3",
            "reset_all": "Numpad0",
            "toggle_overlay": "Numpad.",
        }
        raw_hotkeys = data.get("hotkeys", {})
        if isinstance(raw_hotkeys, dict):
            merged_hotkeys = {**default_hotkeys, **{str(k): str(v) for k, v in raw_hotkeys.items()}}
        else:
            merged_hotkeys = default_hotkeys

        return cls(
            start_in_manual_mode=bool(data.get("start_in_manual_mode", True)),
            reaction_offset=offset,
            restart_on_repeat=bool(data.get("restart_on_repeat", False)),
            sound_on_ready=bool(data.get("sound_on_ready", False)),
            hotkeys=merged_hotkeys,
        )


@dataclass
class AppConfig:
    schema_version: int = 2
    app: AppInfo = field(default_factory=AppInfo)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    manual: ManualSettings = field(default_factory=ManualSettings)
    active_killer_id: str = "the_hidden"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "app": asdict(self.app),
            "capture": self.capture.to_dict(),
            "overlay": self.overlay.to_dict(),
            "manual": self.manual.to_dict(),
            "active_killer_id": str(self.active_killer_id),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Membuat instance AppConfig dari dictionary dengan migrasi otomatis v1 -> v2."""
        if not isinstance(data, dict):
            return cls()

        in_version = int(data.get("schema_version", 1))

        app_raw = data.get("app", {})
        app_info = AppInfo(
            name=str(app_raw.get("name", "Violence District Cooldown Tracker")),
            version=str(app_raw.get("version", "0.2.0-manual")),
            debug_mode=bool(app_raw.get("debug_mode", True)),
        )

        cap_raw = data.get("capture", {})
        capture_settings = CaptureSettings.from_dict(cap_raw)

        ovl_raw = data.get("overlay", {})
        overlay_settings = OverlaySettings.from_dict(ovl_raw)

        # Memuat atau memigrasikan pengaturan manual
        man_raw = data.get("manual", {})
        manual_settings = ManualSettings.from_dict(man_raw)

        killer_id = str(data.get("active_killer_id", "the_hidden")).strip().lower()
        if not killer_id:
            killer_id = "the_hidden"

        if in_version < 2:
            logger.info("Migrated configuration from schema_version %d to 2.", in_version)

        return cls(
            schema_version=2,
            app=app_info,
            capture=capture_settings,
            overlay=overlay_settings,
            manual=manual_settings,
            active_killer_id=killer_id,
        )


class SettingsManager:
    """Manajer konfigurasi runtime aplikasi.
    
    Menyediakan migrasi otomatis antar versi skema serta fallback aman jika file rusak.
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
            logger.info("Configuration file not found at %s. Creating default v2.", target_path)
            self._config = AppConfig()
            self.save(self._config, target_path)
            return self._config

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            in_version = raw_data.get("schema_version", 1)
            self._config = AppConfig.from_dict(raw_data)

            # Jika terjadi migrasi skema, simpan pembaruan ke disk
            if in_version < 2:
                logger.info("Auto-saving migrated v2 configuration to %s", target_path)
                self.save(self._config, target_path)

            logger.info("Successfully loaded application config from %s", target_path)
        except Exception as exc:
            logger.warning("Failed to parse config at %s (%s). Falling back to defaults.", target_path, exc)
            self._config = AppConfig()

        self.path = target_path
        return self._config

    def save(self, config: Optional[AppConfig] = None, path: Optional[Path] = None) -> None:
        target_config = config or self._config or AppConfig()
        target_path = path or self.path

        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(target_config.to_dict(), f, indent=2, ensure_ascii=False)
        tmp_path.replace(target_path)
        self._config = target_config
        logger.info("Saved application config to %s", target_path)
