"""Detection Result Model and AbilityEvent Adapter Contract.

Violence District Cooldown Tracker — Week 3 (Day 17)
Defines a normalized, UI-independent DetectionResult object emitted by CV and audio detectors.
Provides an adapter to convert detection outputs into validated cooldown AbilityEvents (source='vision').
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cooldown.ability_event import AbilityEvent, InvalidAbilityEventError


@dataclass(frozen=True)
class DetectionResult:
    """Model data output deteksi kemampuan Killer dari pipeline Computer Vision / Audio.

    Attributes:
        killer_id: ID killer target (misal: 'the_hidden').
        ability_id: ID kemampuan yang terdeteksi (misal: 'leap').
        event_type: Tipe event aksi ('cast_start', 'release', 'cancel').
        timestamp: Timestamp waktu monotonic absolut saat event terdeteksi (time.monotonic()).
        confidence: Skor keyakinan deteksi (0.0 s.d. 1.0).
        source: Sub-sistem pendeteksi ('vision', 'audio', 'hybrid').
        evidence: Metadata bukti inferensi (skor korelasi template, kecepatan lonjakan, frekuensi spektral).
    """

    killer_id: str
    ability_id: str
    event_type: str
    timestamp: float
    confidence: float
    source: str = "vision"
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Memvalidasi integritas field deteksi."""
        if not self.killer_id or not isinstance(self.killer_id, str):
            raise ValueError("Field 'killer_id' must be a non-empty string.")
        if not self.ability_id or not isinstance(self.ability_id, str):
            raise ValueError("Field 'ability_id' must be a non-empty string.")
        if self.event_type not in AbilityEvent.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{self.event_type}'. Must be one of {AbilityEvent.VALID_EVENT_TYPES}.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} must be between 0.0 and 1.0.")
        if self.timestamp < 0:
            raise ValueError("Timestamp cannot be negative.")

    def to_ability_event(self) -> AbilityEvent:
        """Mengonversi DetectionResult menjadi kontrak AbilityEvent ternormalisasi untuk CooldownManager.

        Returns:
            AbilityEvent dengan source='vision' yang siap dieksekusi oleh CooldownManager.
        """
        return AbilityEvent(
            killer_id=self.killer_id,
            ability_id=self.ability_id,
            event_type=self.event_type,
            timestamp=self.timestamp,
            confidence=self.confidence,
            source="vision",
        )
