from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from validate_json_format import (  # noqa: E402
    JsonFormatError,
    canonical_json_text,
    validate_json_format,
)


class JsonFormatValidationTests(unittest.TestCase):
    def test_canonical_pretty_json_passes(self) -> None:
        value = {"name": "München", "items": [1, {"active": True}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            path.write_text(canonical_json_text(value), encoding="utf-8")
            validate_json_format(path)

    def test_minified_json_is_rejected(self) -> None:
        value = {"name": "München", "items": [1, {"active": True}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            path.write_text(
                json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(JsonFormatError, "not canonically formatted"):
                validate_json_format(path)

    def test_missing_final_newline_is_rejected(self) -> None:
        value = {"status": "pending"}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(JsonFormatError, "not canonically formatted"):
                validate_json_format(path)


if __name__ == "__main__":
    unittest.main()
