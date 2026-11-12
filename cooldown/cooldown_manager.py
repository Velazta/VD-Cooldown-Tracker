"""Deterministic Cooldown State Machine for Violence District Cooldown Tracker.

Week 2 — Day 9 (Cooldown State Machine)
Maintains ability cooldown states (READY, WAITING_FOR_RELEASE, COOLDOWN)
using monotonic clock timestamps, elapsed-time calculations (zero drift),
and duplicate event suppression.
Independent of PySide6 and OpenCV.
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional

from cooldown.ability_event import AbilityEvent
from cooldown.cooldown_state import CooldownSnapshot, CooldownState
from database.database_manager import AbilityConfig
from app.logger import get_logger

logger = get_logger("cooldown")


class CooldownManager:
    """Manajer status cooldown mandiri dan deterministik.

    Mengatur transisi status kemampuan berbasis semantik trigger
    ('on_cast_start' vs 'on_release'), menghitung sisa waktu berbasis
    monotonic clock absolut, dan mengabaikan event pemicu duplikat.
    """

    def __init__(
        self,
        time_func: Optional[Callable[[], float]] = None,
    ) -> None:
        """Inisialisasi CooldownManager.

        Args:
            time_func: Fungsi pengambil waktu (default: time.monotonic).
                       Dapat diinjeksi untuk pengujian clock deterministik/mock.
        """
        self._time_func = time_func or time.monotonic
        self._killer_id: str = ""
        self._ability: Optional[AbilityConfig] = None
        self._state: CooldownState = CooldownState.READY

        # Monotonic timestamps untuk kalkulasi zero-drift
        self._start_timestamp: float = 0.0
        self._end_timestamp: float = 0.0

        # UI-agnostic listeners
        self._listeners: List[Callable[[CooldownSnapshot], None]] = []

    @property
    def state(self) -> CooldownState:
        """Mengambil state aktif saat ini setelah mengevaluasi kemungkinan expiry."""
        self._check_and_update_expiry()
        return self._state

    @property
    def killer_id(self) -> str:
        return self._killer_id

    @property
    def ability(self) -> Optional[AbilityConfig]:
        return self._ability

    def add_listener(self, callback: Callable[[CooldownSnapshot], None]) -> None:
        """Mendaftarkan listener callback yang akan menerima CooldownSnapshot saat state berubah."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[CooldownSnapshot], None]) -> None:
        """Menghapus listener callback yang telah terdaftar."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def set_ability(self, killer_id: str, ability: AbilityConfig) -> None:
        """Memuat konfigurasi kemampuan aktif dari database.

        Args:
            killer_id: ID killer pemilik kemampuan.
            ability: Objek konfigurasi AbilityConfig tervalidasi.
        """
        self._killer_id = killer_id
        self._ability = ability

        # Reset timer saat kemampuan diganti
        self._start_timestamp = 0.0
        self._end_timestamp = 0.0

        if not ability.enabled:
            self._state = CooldownState.DISABLED
        else:
            self._state = CooldownState.READY

        logger.info(
            "Loaded ability '%s' (%s) for killer '%s'. CD: %.1fs | Trigger: %s",
            ability.name,
            ability.id,
            killer_id,
            ability.cooldown_seconds,
            ability.trigger_type,
        )
        self._notify_listeners()

    def handle_event(self, event: AbilityEvent) -> bool:
        """Memproses AbilityEvent masuk dan mengevaluasi transisi status cooldown.

        Args:
            event: Objek AbilityEvent yang telah tervalidasi.

        Returns:
            bool: True jika event memicu perubahan status; False jika event diabaikan/ditekan.
        """
        if self._ability is None:
            logger.warning("Event ignored: No active ability configured.")
            return False

        if not self._ability.enabled:
            logger.debug("Event ignored: Active ability '%s' is disabled.", self._ability.id)
            return False

        # Pastikan event ditujukan untuk killer dan ability aktif saat ini
        if event.killer_id != self._killer_id or event.ability_id != self._ability.id:
            logger.debug(
                "Event ignored: Mismatched target (%s/%s vs active %s/%s).",
                event.killer_id,
                event.ability_id,
                self._killer_id,
                self._ability.id,
            )
            return False

        # Evaluasi apakah cooldown aktif sudah selesai sebelum memproses event baru
        self._check_and_update_expiry()

        # 1. Penanganan Event CANCEL / RESET
        if event.event_type == "cancel":
            if self._state != CooldownState.READY:
                logger.info("Ability '%s' cancelled by event.", self._ability.id)
                self.reset()
                return True
            return False

        # 2. Penekanan Event Duplikat (Duplicate Event Suppression)
        # Jika cooldown sedang berjalan aktif, tolak pemicuan ulang
        if self._state == CooldownState.COOLDOWN:
            logger.debug(
                "Duplicate event '%s' suppressed: Cooldown for '%s' is already active.",
                event.event_type,
                self._ability.id,
            )
            return False

        trigger_type = self._ability.trigger_type

        # 3. Penanganan Berdasarkan trigger_type
        if trigger_type == "on_cast_start":
            if event.event_type == "cast_start":
                self._start_cooldown(event.timestamp)
                return True
            # Event release diabaikan untuk kemampuan on_cast_start
            return False

        elif trigger_type == "on_release":
            if event.event_type == "cast_start":
                if self._state == CooldownState.READY:
                    self._state = CooldownState.WAITING_FOR_RELEASE
                    logger.info("Ability '%s' entered WAITING_FOR_RELEASE stance.", self._ability.id)
                    self._notify_listeners()
                    return True
                return False

            elif event.event_type == "release":
                # Mulai cooldown saat release dilepaskan
                if self._state in (CooldownState.WAITING_FOR_RELEASE, CooldownState.READY):
                    self._start_cooldown(event.timestamp)
                    return True
                return False

        logger.warning("Unhandled trigger_type '%s' for ability '%s'.", trigger_type, self._ability.id)
        return False

    def reset(self) -> None:
        """Mereset status kemampuan kembali ke READY secara deterministik."""
        self._start_timestamp = 0.0
        self._end_timestamp = 0.0
        if self._ability and not self._ability.enabled:
            self._state = CooldownState.DISABLED
        else:
            self._state = CooldownState.READY
        logger.info("CooldownManager reset to READY.")
        self._notify_listeners()

    def cancel(self) -> None:
        """Membatalkan cooldown atau fase ancang-ancang dan kembali ke READY."""
        self.reset()

    def get_snapshot(self) -> CooldownSnapshot:
        """Mengambil snapshot status cooldown saat ini untuk dikonsumsi UI overlay.

        Evaluasi expiry waktu dijalankan setiap kali snapshot diambil.
        """
        self._check_and_update_expiry()

        if self._ability is None:
            return CooldownSnapshot(
                killer_id="",
                ability_id="",
                ability_name="No Ability",
                state=CooldownState.DISABLED,
                remaining_seconds=0.0,
                total_cooldown_seconds=0.0,
                progress=0.0,
                trigger_type="on_cast_start",
                verified=False,
            )

        total_cd = float(self._ability.cooldown_seconds)

        if self._state == CooldownState.COOLDOWN:
            now = self._time_func()
            remaining = max(0.0, self._end_timestamp - now)
            progress = remaining / total_cd if total_cd > 0 else 0.0
        elif self._state == CooldownState.WAITING_FOR_RELEASE:
            remaining = total_cd
            progress = 1.0
        else:
            remaining = 0.0
            progress = 0.0

        return CooldownSnapshot(
            killer_id=self._killer_id,
            ability_id=self._ability.id,
            ability_name=self._ability.name,
            state=self._state,
            remaining_seconds=remaining,
            total_cooldown_seconds=total_cd,
            progress=progress,
            trigger_type=self._ability.trigger_type,
            verified=self._ability.cooldown_verified,
            interact_input=self._ability.interact_input,
        )

    def _start_cooldown(self, trigger_timestamp: float) -> None:
        """Memulai hitungan mundur cooldown berbasis timestamp absolut."""
        assert self._ability is not None
        duration = float(self._ability.cooldown_seconds)
        self._start_timestamp = trigger_timestamp
        self._end_timestamp = trigger_timestamp + duration
        self._state = CooldownState.COOLDOWN

        logger.info(
            "Cooldown STARTED for '%s'. Duration: %.1fs | End Timestamp: %.2f",
            self._ability.id,
            duration,
            self._end_timestamp,
        )
        self._notify_listeners()

    def _check_and_update_expiry(self) -> None:
        """Mengecek apakah waktu cooldown telah habis dan otomatis kembali ke READY."""
        if self._state == CooldownState.COOLDOWN:
            now = self._time_func()
            if now >= self._end_timestamp:
                self._state = CooldownState.READY
                self._start_timestamp = 0.0
                self._end_timestamp = 0.0
                logger.info(
                    "Cooldown EXPIRED for '%s'. State transitioned to READY.",
                    self._ability.id if self._ability else "unknown",
                )
                self._notify_listeners()

    def _notify_listeners(self) -> None:
        """Mengirim snapshot terbaru ke seluruh listener yang terdaftar."""
        snapshot = self.get_snapshot()
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception as exc:
                logger.error("Error in cooldown listener callback: %s", exc)
