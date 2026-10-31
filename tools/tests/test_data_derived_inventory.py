"""Fast consistency guard: data-derived README, contracts, materializers and restore probe agree."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import derived_clean_root_audit  # noqa: E402

DERIVED = ROOT / "data-derived"
README = DERIVED / "README.md"
WORKFLOWS = ROOT / ".github" / "workflows"


def _readme_rows() -> dict[str, tuple[str, str, list[str]]]:
    text = README.read_text(encoding="utf-8")
    block = text.split("<!-- derived-products:start -->")[1].split("<!-- derived-products:end -->")[0]
    rows = {}
    for line in block.splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "Product directory" or set(cells[0]) <= {"-"}:
            continue
        rows[cells[0]] = (cells[1], cells[2], [w.strip().strip("`") for w in cells[3].split(",")])
    return rows


class DataDerivedInventoryTests(unittest.TestCase):
    def test_every_product_directory_is_in_readme(self):
        dirs = {p.name for p in DERIVED.iterdir() if p.is_dir()}
        self.assertEqual(dirs, set(_readme_rows()))

    def test_contract_materializer_and_writer_workflows_exist(self):
        for product, (contract, materializer, writers) in _readme_rows().items():
            with self.subTest(product=product):
                self.assertTrue((ROOT / contract).is_file(), contract)
                self.assertTrue((ROOT / materializer).is_file(), materializer)
                self.assertTrue(writers)
                for w in writers:
                    self.assertTrue((WORKFLOWS / w).is_file(), w)

    def test_every_product_is_in_restore_probe(self):
        self.assertEqual(set(_readme_rows()), set(derived_clean_root_audit.PRODUCTS))


if __name__ == "__main__":
    unittest.main()
