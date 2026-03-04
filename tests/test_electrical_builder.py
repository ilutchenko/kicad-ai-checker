from __future__ import annotations

import unittest
from pathlib import Path

from kischk.kicad.electrical_builder import build_electrical_project


REPO_ROOT = Path(__file__).resolve().parents[1]


class ElectricalBuilderTests(unittest.TestCase):
    def test_builds_project_with_components_and_nets(self) -> None:
        model = build_electrical_project(REPO_ROOT / "test_kicad_project")

        self.assertEqual(len(model.schematics), 4)
        self.assertGreater(len(model.nets), 0)

        all_components = [c for s in model.schematics for c in s.components]
        self.assertGreater(len(all_components), 0)

        connected_pin_count = sum(
            1
            for component in all_components
            for pin in component.pins
            if pin.net_id is not None
        )
        self.assertGreater(connected_pin_count, 0)

    def test_uses_kicad_netlist_codes_and_names(self) -> None:
        model = build_electrical_project(REPO_ROOT / "test_kicad_project")
        all_components = [c for s in model.schematics for c in s.components]

        r14 = next(c for c in all_components if c.reference == "R14")
        pin2 = next(p for p in r14.pins if p.pin_number == "2")

        self.assertEqual(pin2.net_id, "1")
        self.assertEqual(pin2.net_name, "+3.3V")

    def test_extracts_pin_direction_and_reference(self) -> None:
        model = build_electrical_project(REPO_ROOT / "test_kicad_project")
        all_components = [c for s in model.schematics for c in s.components]

        j1 = next(c for c in all_components if c.reference == "J1")
        pin1 = next(p for p in j1.pins if p.pin_number == "1")

        self.assertEqual(j1.lib_id, "Connector_Generic:Conn_02x20_Odd_Even")
        self.assertEqual(pin1.direction, "passive")
        self.assertIsNotNone(pin1.net_id)

    def test_extracts_datasheet_field(self) -> None:
        model = build_electrical_project(REPO_ROOT / "test_kicad_project")
        all_components = [c for s in model.schematics for c in s.components]

        u2 = next(c for c in all_components if c.reference == "U2")
        self.assertIn("maximintegrated", (u2.datasheet or "").lower())

    def test_extracts_description_lcsc_and_custom_fields(self) -> None:
        model = build_electrical_project(REPO_ROOT / "test_kicad_project")
        all_components = [c for s in model.schematics for c in s.components]

        r14 = next(c for c in all_components if c.reference == "R14")
        self.assertEqual(r14.description, "Resistor")
        self.assertEqual(r14.lcsc, "C15401")
        self.assertIsInstance(r14.custom_fields, dict)


if __name__ == "__main__":
    unittest.main()
