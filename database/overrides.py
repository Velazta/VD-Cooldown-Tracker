"""User Cooldown Overrides Manager.

Violence District Cooldown Tracker — Manual Trigger Milestone (Phase M1 / M6)
Manages user overrides for killer ability cooldown durations in 'config/user_overrides.json'.
Preserves original database integrity by applying overrides dynamically at runtime.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.logger import get_logger
from database.database_manager import AbilityConfig, KillerConfig, KillerDatabase

logger = get_logger("overrides")

DEFAULT_OVERRIDES_PATH = Path("config/user_overrides.json")


def get_default_overrides_path() -> Path:
    """Returns the default file path for user overrides."""
    return DEFAULT_OVERRIDES_PATH


def load_user_overrides(path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Loads user overrides from disk safely.
    
    Returns an empty dict if the file does not exist or contains invalid JSON.
    """
    target = Path(path) if path is not None else DEFAULT_OVERRIDES_PATH
    if not target.exists():
        logger.debug("User overrides file not found at %s. Returning empty.", target)
        return {"schema_version": 1, "overrides": {}}

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("User overrides root must be a dict. Ignoring %s.", target)
                return {"schema_version": 1, "overrides": {}}
            if "overrides" not in data or not isinstance(data["overrides"], dict):
                data["overrides"] = {}
            if "schema_version" not in data:
                data["schema_version"] = 1
            return data
    except Exception as exc:
        logger.warning("Failed to parse user overrides from %s: %s. Using defaults.", target, exc)
        return {"schema_version": 1, "overrides": {}}


def save_user_overrides(data: Dict[str, Any], path: Optional[Path | str] = None) -> None:
    """Saves user overrides to disk with clean formatting."""
    target = Path(path) if path is not None else DEFAULT_OVERRIDES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": int(data.get("schema_version", 1)),
        "overrides": data.get("overrides", {}),
    }

    tmp_path = target.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp_path.replace(target)
    logger.info("Saved user overrides to %s", target)


def set_ability_override(
    killer_id: str,
    ability_id: str,
    cooldown_seconds: float,
    verified: bool = False,
    notes: str = "",
    path: Optional[Path | str] = None,
) -> None:
    """Sets or updates a specific ability override."""
    if cooldown_seconds <= 0:
        raise ValueError(f"Cooldown seconds must be positive, got {cooldown_seconds}")

    data = load_user_overrides(path)
    overrides = data.setdefault("overrides", {})
    killer_entry = overrides.setdefault(killer_id.strip().lower(), {})
    killer_entry[ability_id.strip().lower()] = {
        "cooldown_seconds": float(cooldown_seconds),
        "cooldown_verified": bool(verified),
        "notes": str(notes).strip(),
    }
    save_user_overrides(data, path)


def remove_ability_override(
    killer_id: str,
    ability_id: str,
    path: Optional[Path | str] = None,
) -> bool:
    """Removes an ability override, reverting to default database value.
    
    Returns True if an override was removed, False if none existed.
    """
    data = load_user_overrides(path)
    overrides = data.get("overrides", {})
    k_id = killer_id.strip().lower()
    a_id = ability_id.strip().lower()

    if k_id in overrides and a_id in overrides[k_id]:
        del overrides[k_id][a_id]
        if not overrides[k_id]:
            del overrides[k_id]
        save_user_overrides(data, path)
        logger.info("Removed override for %s/%s", k_id, a_id)
        return True
    return False


def apply_overrides_to_killer(
    killer: KillerConfig,
    overrides_data: Optional[Dict[str, Any]] = None,
) -> KillerConfig:
    """Applies user overrides to a KillerConfig instance.
    
    Returns a new KillerConfig instance where overridden abilities have
    source='user' and new cooldown values. Unmodified abilities have source='db'.
    """
    if overrides_data is None:
        overrides_data = load_user_overrides()

    k_id = killer.id.strip().lower()
    killer_overrides = overrides_data.get("overrides", {}).get(k_id, {})

    new_abilities: list[AbilityConfig] = []
    for ab in killer.abilities:
        a_id = ab.id.strip().lower()
        if a_id in killer_overrides:
            ov = killer_overrides[a_id]
            new_ab = AbilityConfig(
                id=ab.id,
                name=ab.name,
                cooldown_seconds=float(ov.get("cooldown_seconds", ab.cooldown_seconds)),
                cooldown_verified=bool(ov.get("cooldown_verified", ab.cooldown_verified)),
                enabled=ab.enabled,
                trigger_type=ab.trigger_type,
                interact_input=ab.interact_input,
                detection_method=ab.detection_method,
                description=ab.description,
                source="user",
                notes=str(ov.get("notes", "")),
            )
            new_abilities.append(new_ab)
        else:
            new_ab = AbilityConfig(
                id=ab.id,
                name=ab.name,
                cooldown_seconds=ab.cooldown_seconds,
                cooldown_verified=ab.cooldown_verified,
                enabled=ab.enabled,
                trigger_type=ab.trigger_type,
                interact_input=ab.interact_input,
                detection_method=ab.detection_method,
                description=ab.description,
                source="db",
                notes=ab.notes,
            )
            new_abilities.append(new_ab)

    return KillerConfig(
        id=killer.id,
        name=killer.name,
        description=killer.description,
        abilities=new_abilities,
    )


def apply_overrides_to_database(
    db: KillerDatabase,
    overrides_data: Optional[Dict[str, Any]] = None,
) -> KillerDatabase:
    """Applies user overrides to all killers in a KillerDatabase instance."""
    if overrides_data is None:
        overrides_data = load_user_overrides()

    new_killers = [apply_overrides_to_killer(k, overrides_data) for k in db.killers]
    return KillerDatabase(
        schema_version=db.schema_version,
        game=db.game,
        last_updated=db.last_updated,
        killers=new_killers,
    )
