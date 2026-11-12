"""Cooldown State & Snapshot Models for Violence District Cooldown Tracker.

Week 2 — Day 8 (Desain Kontrak Cooldown)
Defines finite cooldown states and immutable status snapshots for UI-agnostic communication.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CooldownState(str, Enum):
    """Status diskrit kemampuan Killer dalam State Machine."""

    READY = "READY"
    """Kemampuan siap digunakan (tidak ada cooldown aktif)."""

    WAITING_FOR_RELEASE = "WAITING_FOR_RELEASE"
    """Kemampuan bertipe 'on_release' sedang dalam fase ancang-ancang/stance;
    cooldown belum mulai berjalan sampai tombol/serangan dilepaskan."""

    COOLDOWN = "COOLDOWN"
    """Hitungan mundur cooldown sedang aktif berjalan."""

    DISABLED = "DISABLED"
    """Kemampuan dinonaktifkan dalam konfigurasi database."""


@dataclass(frozen=True)
class CooldownSnapshot:
    """Snapshot data status cooldown pada satu titik waktu tertentu (immutable).

    Didesain untuk dikirimkan ke controller dan widget visual overlay
    tanpa membiarkan UI memutasi state internal CooldownManager.
    """

    killer_id: str
    ability_id: str
    ability_name: str
    state: CooldownState
    remaining_seconds: float
    total_cooldown_seconds: float
    progress: float  # Rentang 0.0 (selesai/READY) hingga 1.0 (baru mulai)
    trigger_type: str  # 'on_cast_start' | 'on_release'
    verified: bool = False
    interact_input: str = ""

    def __post_init__(self) -> None:
        # Clamping nilai numerik agar aman bagi widget UI
        rem = max(0.0, float(self.remaining_seconds))
        tot = max(0.0, float(self.total_cooldown_seconds))
        prog = max(0.0, min(1.0, float(self.progress)))

        object.__setattr__(self, "remaining_seconds", rem)
        object.__setattr__(self, "total_cooldown_seconds", tot)
        object.__setattr__(self, "progress", prog)

    @property
    def is_ready(self) -> bool:
        """True jika kemampuan berada dalam kondisi READY."""
        return self.state == CooldownState.READY

    @property
    def is_active(self) -> bool:
        """True jika cooldown sedang berjalan atau sedang menunggu release."""
        return self.state in (CooldownState.COOLDOWN, CooldownState.WAITING_FOR_RELEASE)

    @property
    def is_waiting_for_release(self) -> bool:
        """True jika berada dalam fase ancang-ancang menunggu pelepasan aksi."""
        return self.state == CooldownState.WAITING_FOR_RELEASE

    @property
    def formatted_remaining(self) -> str:
        """String terformat sisa detik (misal '24.5s' atau 'READY')."""
        if self.state == CooldownState.READY:
            return "READY"
        if self.state == CooldownState.WAITING_FOR_RELEASE:
            return "AIMING"
        if self.state == CooldownState.DISABLED:
            return "DISABLED"
        return f"{self.remaining_seconds:.1f}s"
