"""
Local Killer & Ability Database Manager
Violence District Cooldown Tracker — Day 6 (Poin 6.2)
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from app.logger import get_logger

logger = get_logger("database")


class DatabaseError(Exception):
    """Base exception untuk seluruh error pada modul database."""
    pass


class DatabaseValidationError(DatabaseError):
    """Dilempar ketika struktur atau nilai data JSON melanggar aturan skema."""
    pass


class DatabaseNotFoundError(DatabaseError):
    """Dilempar ketika file database tidak ditemukan di disk."""
    pass


@dataclass
class AbilityConfig:
    """Model data strongly-typed untuk satu kemampuan (ability) killer."""
    id: str
    name: str
    cooldown_seconds: float
    cooldown_verified: bool = False
    enabled: bool = True
    trigger_type: str = "on_cast_start"    # 'on_cast_start' (Leap/Mark) atau 'on_release' (Veil spear)
    interact_input: str = ""                # Tombol/interaksi trigger (E Button, Right Click, dll)
    detection_method: str = "pose_sequence" # 'pose_sequence', 'pose_release', 'visual_indicator'
    description: str = ""

    def validate(self) -> None:
        """Memvalidasi integritas data kemampuan."""
        if not self.id or not isinstance(self.id, str):
            raise DatabaseValidationError("Field 'id' pada ability wajib diisi dan berupa string.")
        if not self.name or not isinstance(self.name, str):
            raise DatabaseValidationError(f"Field 'name' pada ability '{self.id}' wajib diisi.")
        if not isinstance(self.cooldown_seconds, (int, float)) or self.cooldown_seconds <= 0:
            raise DatabaseValidationError(
                f"Cooldown '{self.id}' harus berupa angka positif dalam detik (diterima: {self.cooldown_seconds})."
            )
        if self.trigger_type not in ("on_cast_start", "on_release", "passive"):
            raise DatabaseValidationError(
                f"trigger_type '{self.trigger_type}' pada '{self.id}' tidak valid. "
                "Pilihan: 'on_cast_start', 'on_release', 'passive'."
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AbilityConfig":
        if not isinstance(data, dict):
            raise DatabaseValidationError(f"Data ability harus berupa objek JSON/dict (diterima: {type(data)}).")
        
        ability = cls(
            id=str(data.get("id", "")).strip().lower(),
            name=str(data.get("name", "")).strip(),
            cooldown_seconds=float(data.get("cooldown_seconds", 0.0)),
            cooldown_verified=bool(data.get("cooldown_verified", False)),
            enabled=bool(data.get("enabled", True)),
            trigger_type=str(data.get("trigger_type", "on_cast_start")).strip(),
            interact_input=str(data.get("interact_input", "")).strip(),
            detection_method=str(data.get("detection_method", "pose_sequence")).strip(),
            description=str(data.get("description", "")).strip()
        )
        ability.validate()
        return ability

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KillerConfig:
    """Model data strongly-typed untuk satu karakter Killer."""
    id: str
    name: str
    description: str = ""
    abilities: List[AbilityConfig] = field(default_factory=list)

    def validate(self) -> None:
        """Memvalidasi integritas data killer dan daftar kemampuannya."""
        if not self.id or not isinstance(self.id, str):
            raise DatabaseValidationError("Field 'id' pada killer wajib diisi dan berupa string.")
        if not self.name or not isinstance(self.name, str):
            raise DatabaseValidationError(f"Field 'name' pada killer '{self.id}' wajib diisi.")

        seen_abilities = set()
        for ability in self.abilities:
            ability.validate()
            if ability.id in seen_abilities:
                raise DatabaseValidationError(
                    f"Duplikat ability ID '{ability.id}' terdeteksi pada killer '{self.id}'."
                )
            seen_abilities.add(ability.id)

    def get_ability(self, ability_id: str) -> Optional[AbilityConfig]:
        """Mencari ability milik killer ini berdasarkan ID."""
        target_id = ability_id.strip().lower()
        for ability in self.abilities:
            if ability.id == target_id:
                return ability
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KillerConfig":
        if not isinstance(data, dict):
            raise DatabaseValidationError(f"Data killer harus berupa objek JSON/dict (diterima: {type(data)}).")

        raw_abilities = data.get("abilities", [])
        if not isinstance(raw_abilities, list):
            raise DatabaseValidationError(f"Field 'abilities' pada killer '{data.get('id')}' harus berupa list.")

        abilities = [AbilityConfig.from_dict(a) for a in raw_abilities]

        killer = cls(
            id=str(data.get("id", "")).strip().lower(),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            abilities=abilities
        )
        killer.validate()
        return killer

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KillerDatabase:
    """Model root untuk seluruh basis data killer lokal."""
    schema_version: int = 1
    game: str = "Violence District"
    last_updated: str = ""
    killers: List[KillerConfig] = field(default_factory=list)

    def validate(self) -> None:
        """Memvalidasi integritas root database."""
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise DatabaseValidationError(f"schema_version tidak valid: {self.schema_version}")

        seen_killers = set()
        for killer in self.killers:
            killer.validate()
            if killer.id in seen_killers:
                raise DatabaseValidationError(f"Duplikat killer ID '{killer.id}' terdeteksi dalam database.")
            seen_killers.add(killer.id)

    def get_killer(self, killer_id: str) -> Optional[KillerConfig]:
        """Mengambil objek killer berdasarkan ID (misal: 'the_hidden', 'veil')."""
        target_id = killer_id.strip().lower()
        for killer in self.killers:
            if killer.id == target_id:
                return killer
        return None

    def get_ability(self, killer_id: str, ability_id: str) -> Optional[AbilityConfig]:
        """Mengambil objek ability spesifik langsung."""
        killer = self.get_killer(killer_id)
        if killer:
            return killer.get_ability(ability_id)
        return None

    def list_killer_ids(self) -> List[str]:
        """Mengembalikan daftar seluruh ID killer yang tersedia."""
        return [k.id for k in self.killers]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KillerDatabase":
        if not isinstance(data, dict):
            raise DatabaseValidationError("Root JSON database harus berupa object dictionary.")

        raw_killers = data.get("killers", [])
        if not isinstance(raw_killers, list):
            raise DatabaseValidationError("Field 'killers' harus berupa array list.")

        killers = [KillerConfig.from_dict(k) for k in raw_killers]

        db = cls(
            schema_version=int(data.get("schema_version", 1)),
            game=str(data.get("game", "Violence District")),
            last_updated=str(data.get("last_updated", "")),
            killers=killers
        )
        db.validate()
        return db

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatabaseManager:
    """
    Manajer persistence dan query data killer lokal.
    Menangani I/O file JSON aman, validasi schema, dan update cooldown in-memory/disk.
    """

    DEFAULT_PATH = Path("database/killerDatabase.json")

    def __init__(self, database_path: Optional[Path] = None):
        self.path = database_path or self.DEFAULT_PATH
        self._database: Optional[KillerDatabase] = None

    @property
    def database(self) -> KillerDatabase:
        """Mengakses database aktif, otomatis meload dari disk jika belum dimuat."""
        if self._database is None:
            self.load()
        return self._database

    def load(self, path: Optional[Path] = None) -> KillerDatabase:
        """
        Membaca dan memvalidasi file JSON dari disk.
        Menghasilkan error yang ramah dan mudah dipahami jika file korup atau salah format.
        """
        target_path = path or self.path
        if not target_path.exists():
            logger.error("Database file not found at: %s", target_path)
            raise DatabaseNotFoundError(f"File database tidak ditemukan di: {target_path}")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as err:
            logger.error("Database JSON decode error at %s: %s", target_path, err)
            raise DatabaseValidationError(
                f"Sintaks JSON rusak pada {target_path} (Baris {err.lineno}, Kolom {err.colno}): {err.msg}"
            ) from err
        except Exception as exc:
            logger.error("Failed to read database file %s: %s", target_path, exc)
            raise DatabaseError(f"Gagal membaca file {target_path}: {exc}") from exc

        self._database = KillerDatabase.from_dict(raw_data)
        self.path = target_path
        logger.info(
            "Successfully loaded killer database from %s (schema_version: %d, killers: %d)",
            target_path,
            self._database.schema_version,
            len(self._database.killers),
        )
        return self._database

    def save(self, path: Optional[Path] = None) -> None:
        """
        Menyimpan kondisi database saat ini ke disk secara rapi (indent=2).
        """
        if self._database is None:
            raise DatabaseError("Tidak ada data database yang dimuat untuk disimpan.")

        target_path = path or self.path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(self._database.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info("Saved database to %s", target_path)
        except Exception as exc:
            logger.error("Failed to save database to %s: %s", target_path, exc)
            raise DatabaseError(f"Gagal menyimpan database ke {target_path}: {exc}") from exc

    def get_killer(self, killer_id: str) -> Optional[KillerConfig]:
        """Query shortcut: mencari killer berdasarkan ID."""
        return self.database.get_killer(killer_id)

    def get_ability(self, killer_id: str, ability_id: str) -> Optional[AbilityConfig]:
        """Query shortcut: mencari ability milik killer tertentu."""
        return self.database.get_ability(killer_id, ability_id)

    def update_cooldown(
        self,
        killer_id: str,
        ability_id: str,
        new_seconds: float,
        mark_verified: bool = True,
        auto_save: bool = True
    ) -> bool:
        """
        Memperbarui durasi cooldown satu ability secara aman.
        Jika auto_save=True, perubahan langsung ditulis ke file JSON.
        """
        ability = self.get_ability(killer_id, ability_id)
        if ability is None:
            return False

        if not isinstance(new_seconds, (int, float)) or new_seconds <= 0:
            raise DatabaseValidationError(
                f"Durasi cooldown baru harus berupa angka positif dalam detik (diterima: {new_seconds})."
            )

        ability.cooldown_seconds = float(new_seconds)
        ability.cooldown_verified = mark_verified

        if auto_save:
            self.save()

        return True
