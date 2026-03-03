from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kischk.kicad.project import load_project
from kischk.kicad.sch_model import SExprAtom
from kischk.kicad.sch_parser import SchematicParseError, parse_loaded_project, parse_schematic_file


REPO_ROOT = Path(__file__).resolve().parents[1]


class SchematicParserTests(unittest.TestCase):
    def test_parses_sample_project_files(self) -> None:
        loaded = load_project(REPO_ROOT / "test_kicad_project")

        parsed = parse_loaded_project(loaded)

        self.assertEqual(len(parsed.schematics), 4)
        for sch in parsed.schematics:
            self.assertTrue(sch.root.items)
            self.assertIsInstance(sch.root.items[0], SExprAtom)
            self.assertEqual(sch.root.items[0].value, "kicad_sch")

    def test_parses_single_schematic_file(self) -> None:
        path = REPO_ROOT / "test_kicad_project" / "mcu.kicad_sch"

        parsed = parse_schematic_file(path)

        self.assertEqual(parsed.path.name, "mcu.kicad_sch")
        self.assertEqual(parsed.root.items[0].value, "kicad_sch")

    def test_reports_location_for_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "broken.kicad_sch"
            bad_file.write_text('(kicad_sch\n  (wire\n    (pts (xy 1 2))\n', encoding="utf-8")

            with self.assertRaises(SchematicParseError) as ctx:
                parse_schematic_file(bad_file)

            message = str(ctx.exception)
            self.assertIn("broken.kicad_sch", message)
            self.assertIn(": unexpected end of input; missing ')'", message)


if __name__ == "__main__":
    unittest.main()
