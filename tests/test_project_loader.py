from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kischk.kicad.project import ProjectLoaderError, load_project


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectLoaderTests(unittest.TestCase):
    def test_loads_sample_project_hierarchy(self) -> None:
        project_root = REPO_ROOT / "test_kicad_project"

        loaded = load_project(project_root)

        self.assertEqual(loaded.project_file.name, "slot-rs232-pi-hat.kicad_pro")
        self.assertEqual(loaded.root_schematic.name, "slot-rs232-pi-hat.kicad_sch")

        names = {path.name for path in loaded.schematic_files}
        self.assertSetEqual(
            names,
            {
                "slot-rs232-pi-hat.kicad_sch",
                "mcu.kicad_sch",
                "power_supply.kicad_sch",
                "rs232.kicad_sch",
            },
        )

    def test_raises_when_child_sheet_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "demo.kicad_pro").write_text("{}", encoding="utf-8")
            (root / "demo.kicad_sch").write_text(
                '(kicad_sch\n  (sheet\n    (property "Sheetfile" "child.kicad_sch")\n  )\n)\n',
                encoding="utf-8",
            )

            with self.assertRaises(ProjectLoaderError):
                load_project(root)

    def test_raises_when_ambiguous_root_without_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
            (root / "b.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")

            with self.assertRaises(ProjectLoaderError):
                load_project(root)


if __name__ == "__main__":
    unittest.main()
