import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib import common as common_mod


class NflSourceCommonTests(unittest.TestCase):
    def test_load_json_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bom.json"
            path.write_bytes(b'\xef\xbb\xbf{"a": 1}\n')
            self.assertEqual({"a": 1}, common_mod.load_json(path))

    def test_load_json_still_accepts_plain_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.json"
            path.write_text('{"a": 1}\n', encoding="utf-8")
            self.assertEqual({"a": 1}, common_mod.load_json(path))


if __name__ == "__main__":
    unittest.main()
