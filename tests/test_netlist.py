from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kischk.kicad.netlist import parse_netlist_file


class NetlistTests(unittest.TestCase):
    def test_parses_kicad_sexpr_nets(self) -> None:
        content = '''
(export (version "E")
  (nets
    (net (code "1") (name "+3.3V") (class "Default")
      (node (ref "R14") (pin "2") (pintype "passive"))
      (node (ref "U7") (pin "1") (pinfunction "VBAT") (pintype "power_in")))
    (net (code "2") (name "GND") (class "Default")
      (node (ref "R14") (pin "1") (pintype "passive")))))
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            net = Path(tmpdir) / "sample.net"
            net.write_text(content, encoding="utf-8")

            parsed = parse_netlist_file(net)

            self.assertEqual(len(parsed.nets), 2)
            self.assertEqual(parsed.nets[0].code, "1")
            self.assertEqual(parsed.nets[0].name, "+3.3V")
            self.assertEqual(parsed.nets[0].nodes[1].ref, "U7")
            self.assertEqual(parsed.nets[0].nodes[1].pin, "1")
            self.assertEqual(parsed.nets[0].nodes[1].pintype, "power_in")


if __name__ == "__main__":
    unittest.main()
