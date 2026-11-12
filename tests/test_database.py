"""
Unit Tests for Database Manager & Killer Schema
Violence District Cooldown Tracker — Day 6 (Poin 6.3)
"""
import unittest
import json
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database_manager import (
    DatabaseManager, KillerDatabase, KillerConfig, AbilityConfig,
    DatabaseValidationError, DatabaseNotFoundError
)


class TestDatabaseManager(unittest.TestCase):
    """Pengujian Unit komprehensif untuk Database Manager."""

    def setUp(self):
        self.manager = DatabaseManager()

    def test_load_real_database(self):
        """Memastikan file killerDatabase.json asli dapat dimuat dan divalidasi."""
        db = self.manager.load()
        self.assertIsInstance(db, KillerDatabase)
        self.assertEqual(db.schema_version, 1)
        self.assertEqual(db.game, "Violence District")
        self.assertIn("the_hidden", db.list_killer_ids())
        self.assertIn("veil", db.list_killer_ids())

    def test_query_killer_and_abilities(self):
        """Memverifikasi query killer dan ability berhasil mengambil atribut spesifik."""
        # Query The Hidden
        hidden = self.manager.get_killer("the_hidden")
        self.assertIsNotNone(hidden)
        self.assertEqual(hidden.name, "The Hidden")

        leap = hidden.get_ability("leap")
        self.assertIsNotNone(leap)
        self.assertEqual(leap.cooldown_seconds, 25.0)
        self.assertEqual(leap.trigger_type, "on_cast_start")
        self.assertEqual(leap.interact_input, "E Button")

        # Query Veil
        veil = self.manager.get_killer("veil")
        self.assertIsNotNone(veil)
        spear = veil.get_ability("through_the_veil")
        self.assertIsNotNone(spear)
        self.assertEqual(spear.cooldown_seconds, 20.0)
        self.assertEqual(spear.trigger_type, "on_release")

    def test_missing_file_raises_not_found(self):
        """Memastikan error DatabaseNotFoundError dilempar jika file tidak ada."""
        fake_path = Path("database/non_existent_file_12345.json")
        with self.assertRaises(DatabaseNotFoundError):
            self.manager.load(fake_path)

    def test_malformed_json_raises_validation_error(self):
        """Memastikan sintaks JSON rusak terdeteksi dengan pesan baris/kolom."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            tmp.write("{ invalid_json: true, ")  # JSON tidak ditutup
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(DatabaseValidationError) as ctx:
                self.manager.load(tmp_path)
            self.assertIn("Sintaks JSON rusak", str(ctx.exception))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_negative_cooldown_raises_validation_error(self):
        """Memastikan cooldown bernilai negatif atau 0 ditolak."""
        invalid_data = {
            "schema_version": 1,
            "game": "Test",
            "killers": [
                {
                    "id": "killer1",
                    "name": "Killer One",
                    "abilities": [
                        {"id": "skill1", "name": "Skill", "cooldown_seconds": -10.0}
                    ]
                }
            ]
        }
        with self.assertRaises(DatabaseValidationError) as ctx:
            KillerDatabase.from_dict(invalid_data)
        self.assertIn("angka positif", str(ctx.exception))

    def test_duplicate_killer_id_raises_validation_error(self):
        """Memastikan duplikat ID killer dicegah."""
        invalid_data = {
            "schema_version": 1,
            "game": "Test",
            "killers": [
                {"id": "same_id", "name": "Killer A", "abilities": []},
                {"id": "same_id", "name": "Killer B", "abilities": []}
            ]
        }
        with self.assertRaises(DatabaseValidationError) as ctx:
            KillerDatabase.from_dict(invalid_data)
        self.assertIn("Duplikat killer ID", str(ctx.exception))

    def test_duplicate_ability_id_raises_validation_error(self):
        """Memastikan duplikat ID ability pada satu killer dicegah."""
        invalid_data = {
            "schema_version": 1,
            "game": "Test",
            "killers": [
                {
                    "id": "killer1",
                    "name": "Killer One",
                    "abilities": [
                        {"id": "skill_a", "name": "Skill 1", "cooldown_seconds": 10.0},
                        {"id": "skill_a", "name": "Skill 2", "cooldown_seconds": 20.0}
                    ]
                }
            ]
        }
        with self.assertRaises(DatabaseValidationError) as ctx:
            KillerDatabase.from_dict(invalid_data)
        self.assertIn("Duplikat ability ID", str(ctx.exception))

    def test_invalid_trigger_type_raises_validation_error(self):
        """Memastikan trigger_type yang tidak dikenal ditolak."""
        invalid_data = {
            "schema_version": 1,
            "game": "Test",
            "killers": [
                {
                    "id": "killer1",
                    "name": "Killer One",
                    "abilities": [
                        {"id": "skill1", "name": "Skill", "cooldown_seconds": 15.0, "trigger_type": "unknown_trigger"}
                    ]
                }
            ]
        }
        with self.assertRaises(DatabaseValidationError) as ctx:
            KillerDatabase.from_dict(invalid_data)
        self.assertIn("trigger_type", str(ctx.exception))

    def test_update_cooldown_in_memory(self):
        """Memastikan method update_cooldown memperbarui nilai dan status verifikasi."""
        db = self.manager.load()
        orig_cd = self.manager.get_ability("the_hidden", "leap").cooldown_seconds

        # Update tanpa auto-save ke disk
        success = self.manager.update_cooldown("the_hidden", "leap", 22.5, mark_verified=True, auto_save=False)
        self.assertTrue(success)

        updated_ability = self.manager.get_ability("the_hidden", "leap")
        self.assertEqual(updated_ability.cooldown_seconds, 22.5)
        self.assertTrue(updated_ability.cooldown_verified)

        # Kembalikan ke durasi awal
        self.manager.update_cooldown("the_hidden", "leap", orig_cd, mark_verified=False, auto_save=False)


if __name__ == "__main__":
    unittest.main()
