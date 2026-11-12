"""Normalized Ability Event Contract for Violence District Cooldown Tracker.

Week 2 — Day 8 (Desain Kontrak Cooldown)
Provides a UI-independent and CV-independent data contract for ability trigger events.
Used by manual test buttons, hotkey listeners, and future visual detectors (Week 3/4).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import ClassVar, Set


class InvalidAbilityEventError(ValueError):
    """Dilempar ketika data AbilityEvent melanggar aturan integritas atau tipe event."""
    pass


@dataclass(frozen=True)
class AbilityEvent:
    """Model data ternormalisasi untuk setiap event aksi kemampuan Killer.

    Attributes:
        killer_id: ID unik killer (misal 'the_hidden', 'veil').
        ability_id: ID unik kemampuan (misal 'leap', 'mark', 'through_the_veil').
        event_type: Tipe aksi event ('cast_start', 'release', 'cancel').
        timestamp: Waktu monotonic absolut saat event terjadi (time.monotonic()).
        confidence: Nilai keyakinan event (0.0 - 1.0, default 1.0 untuk manual/hotkey).
        source: Sumber asal event ('manual', 'hotkey', 'vision', 'simulated').
    """

    killer_id: str
    ability_id: str
    event_type: str
    timestamp: float
    confidence: float = 1.0
    source: str = "manual"

    # Himpunan tipe event dan sumber yang diizinkan
    VALID_EVENT_TYPES: ClassVar[Set[str]] = {"cast_start", "release", "cancel"}
    VALID_SOURCES: ClassVar[Set[str]] = {"manual", "hotkey", "vision", "simulated"}

    def __post_init__(self) -> None:
        """Memvalidasi integritas field setelah instantiasi."""
        self.validate()

    def validate(self) -> None:
        """Memvalidasi seluruh field sesuai aturan kontrak.

        Raises:
            InvalidAbilityEventError: Jika ada field yang kosong, bernilai negatif,
            atau melanggar batasan enum string.
        """
        if not self.killer_id or not isinstance(self.killer_id, str):
            raise InvalidAbilityEventError("Field 'killer_id' wajib diisi berupa string non-kosong.")

        if not self.ability_id or not isinstance(self.ability_id, str):
            raise InvalidAbilityEventError("Field 'ability_id' wajib diisi berupa string non-kosong.")

        if self.event_type not in self.VALID_EVENT_TYPES:
            raise InvalidAbilityEventError(
                f"event_type '{self.event_type}' tidak valid. Pilihan: {sorted(self.VALID_EVENT_TYPES)}"
            )

        if not isinstance(self.timestamp, (int, float)) or self.timestamp <= 0:
            raise InvalidAbilityEventError(
                f"timestamp harus berupa nilai float positif monotonic (diterima: {self.timestamp})."
            )

        if not isinstance(self.confidence, (int, float)) or not (0.0 <= self.confidence <= 1.0):
            raise InvalidAbilityEventError(
                f"confidence harus bernilai antara 0.0 s/d 1.0 (diterima: {self.confidence})."
            )

        if self.source not in self.VALID_SOURCES:
            raise InvalidAbilityEventError(
                f"source '{self.source}' tidak valid. Pilihan: {sorted(self.VALID_SOURCES)}"
            )

    @classmethod
    def create(
        cls,
        killer_id: str,
        ability_id: str,
        event_type: str,
        timestamp: float | None = None,
        confidence: float = 1.0,
        source: str = "manual",
    ) -> AbilityEvent:
        """Helper factory untuk instansiasi AbilityEvent dengan timestamp monotonic otomatis."""
        ts = timestamp if timestamp is not None else time.monotonic()
        return cls(
            killer_id=killer_id,
            ability_id=ability_id,
            event_type=event_type,
            timestamp=float(ts),
            confidence=float(confidence),
            source=source,
        )
