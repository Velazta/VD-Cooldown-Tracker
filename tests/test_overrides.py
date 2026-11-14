"""Unit tests for user cooldown overrides (database/overrides.py)."""

import json
from pathlib import Path
import pytest

from database.database_manager import AbilityConfig, KillerConfig, KillerDatabase
from database.overrides import (
    apply_overrides_to_database,
    apply_overrides_to_killer,
    load_user_overrides,
    remove_ability_override,
    save_user_overrides,
    set_ability_override,
)


@pytest.fixture
def sample_killer() -> KillerConfig:
    return KillerConfig(
        id="the_hidden",
        name="The Hidden",
        abilities=[
            AbilityConfig(
                id="leap",
                name="Leap",
                cooldown_seconds=25.0,
                cooldown_verified=False,
                source="db",
                notes="",
            ),
            AbilityConfig(
                id="mark",
                name="Mark",
                cooldown_seconds=15.0,
                cooldown_verified=False,
                source="db",
                notes="",
            ),
        ],
    )


def test_load_missing_overrides_returns_empty_schema(tmp_path: Path):
    missing_file = tmp_path / "does_not_exist.json"
    data = load_user_overrides(missing_file)
    assert data["schema_version"] == 1
    assert data["overrides"] == {}


def test_load_corrupted_overrides_returns_empty_fallback(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{not valid json!!", encoding="utf-8")
    data = load_user_overrides(corrupt_file)
    assert data["schema_version"] == 1
    assert data["overrides"] == {}


def test_save_and_load_overrides(tmp_path: Path):
    target = tmp_path / "overrides.json"
    payload = {
        "schema_version": 1,
        "overrides": {
            "the_hidden": {
                "leap": {
                    "cooldown_seconds": 23.5,
                    "cooldown_verified": True,
                    "notes": "Verified frame count",
                }
            }
        },
    }
    save_user_overrides(payload, target)
    loaded = load_user_overrides(target)
    assert loaded["overrides"]["the_hidden"]["leap"]["cooldown_seconds"] == 23.5
    assert loaded["overrides"]["the_hidden"]["leap"]["cooldown_verified"] is True
    assert loaded["overrides"]["the_hidden"]["leap"]["notes"] == "Verified frame count"


def test_set_and_remove_ability_override(tmp_path: Path):
    target = tmp_path / "overrides.json"
    set_ability_override(
        killer_id="the_hidden",
        ability_id="leap",
        cooldown_seconds=22.0,
        verified=True,
        notes="Stopwatch test",
        path=target,
    )

    loaded = load_user_overrides(target)
    assert "the_hidden" in loaded["overrides"]
    assert loaded["overrides"]["the_hidden"]["leap"]["cooldown_seconds"] == 22.0

    # Removing non-existent override returns False
    removed_fake = remove_ability_override("the_hidden", "fake_ability", path=target)
    assert removed_fake is False

    # Removing existing override returns True
    removed = remove_ability_override("the_hidden", "leap", path=target)
    assert removed is True

    # Database for that killer should now be clean
    loaded_after = load_user_overrides(target)
    assert "the_hidden" not in loaded_after.get("overrides", {})


def test_apply_overrides_to_killer(sample_killer: KillerConfig, tmp_path: Path):
    target = tmp_path / "overrides.json"
    set_ability_override(
        killer_id="the_hidden",
        ability_id="leap",
        cooldown_seconds=20.0,
        verified=True,
        notes="Player measured",
        path=target,
    )

    overrides_data = load_user_overrides(target)
    updated_killer = apply_overrides_to_killer(sample_killer, overrides_data)

    leap_ab = updated_killer.get_ability("leap")
    assert leap_ab is not None
    assert leap_ab.cooldown_seconds == 20.0
    assert leap_ab.cooldown_verified is True
    assert leap_ab.source == "user"
    assert leap_ab.notes == "Player measured"

    mark_ab = updated_killer.get_ability("mark")
    assert mark_ab is not None
    assert mark_ab.cooldown_seconds == 15.0  # untouched
    assert mark_ab.source == "db"


def test_apply_overrides_to_database(sample_killer: KillerConfig, tmp_path: Path):
    db = KillerDatabase(schema_version=1, killers=[sample_killer])
    target = tmp_path / "overrides.json"
    set_ability_override(
        killer_id="the_hidden",
        ability_id="mark",
        cooldown_seconds=12.0,
        verified=True,
        notes="Mark buff patch",
        path=target,
    )

    overrides_data = load_user_overrides(target)
    updated_db = apply_overrides_to_database(db, overrides_data)

    mark_ab = updated_db.get_ability("the_hidden", "mark")
    assert mark_ab is not None
    assert mark_ab.cooldown_seconds == 12.0
    assert mark_ab.source == "user"
