"""Unit and Integration Tests for Template Builder Module.

Violence District Cooldown Tracker — Week 3 (Day 16)
Verifies:
- Extraction of canonical humanoid templates with realistic aspect ratios
- Absence of full-screen camera flick artifacts in templates
- Template manifest integrity
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestTemplateBuilder(unittest.TestCase):
    """Test suite untuk TemplateBuilder."""

    def setUp(self) -> None:
        self.manifest_file = PROJECT_ROOT / "dataset" / "templates" / "the_hidden" / "templates_manifest.json"
        self.template_dir = PROJECT_ROOT / "dataset" / "templates" / "the_hidden"

    def test_templates_manifest_and_dimensions_sanity(self) -> None:
        """Memastikan seluruh template memiliki proporsi humanoid yang realistis (tidak ada artifak layar penuh)."""
        self.assertTrue(self.manifest_file.exists())
        with open(self.manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["killer_id"], "the_hidden")
        self.assertGreaterEqual(data["total_templates"], 10)

        templates = data["templates"]
        for tmpl in templates:
            # Tidak boleh ada template selebar layar penuh (1280 px)
            self.assertLess(tmpl["width"], 800)
            self.assertLess(tmpl["height"], 650)
            self.assertGreaterEqual(tmpl["width"], 50)
            self.assertGreaterEqual(tmpl["height"], 70)

            # Aspek rasio harus realistis untuk humanoid (0.25 - 1.60)
            self.assertGreaterEqual(tmpl["aspect_ratio"], 0.25)
            self.assertLessEqual(tmpl["aspect_ratio"], 1.60)

            # Verifikasi berkas fisik template ada di disk
            tmpl_path = self.template_dir / f"{tmpl['template_id']}.png"
            self.assertTrue(tmpl_path.exists())


if __name__ == "__main__":
    unittest.main()
