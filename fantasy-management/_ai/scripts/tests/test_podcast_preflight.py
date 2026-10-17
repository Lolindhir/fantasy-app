"""No network/source publisher; synthetic coverage checks for local preflight."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from podcast_preflight import check, load_srt, main, propose


SRT = """1
00:00:01,000 --> 00:00:08,000
Romo Dunze ist besser als Ferguson. Die Coaches haben Bedenken.

2
00:00:08,000 --> 00:00:14,000
Jets blitzen oft, aber sie erzeugen wenig Pressure.
"""


class PodcastPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.srt = self.root / "test.srt"
        self.srt.write_text(SRT, encoding="utf-8")

    def test_generates_separate_entity_and_claim_candidates(self):
        digest, cues, _ = load_srt(self.srt)
        result = propose(cues, digest)
        raw_names = [entry["raw"] for entry in result["entities"]]
        self.assertTrue(any("Romo Dunze" in name for name in raw_names))
        self.assertTrue(any("Ferguson" in name for name in raw_names))
        self.assertFalse(any(". Die" in name for name in raw_names))
        self.assertGreaterEqual(len(result["claims"]), 2)
        self.assertTrue(check(cues, digest, result)["ok"])

    def test_transcript_digest_and_exact_raw_offsets_guard(self):
        digest, cues, _ = load_srt(self.srt)
        result = propose(cues, digest)
        result["entities"][0]["raw"] = "Odunze"
        self.assertFalse(check(cues, digest, result)["ok"])
        result = propose(cues, digest)
        self.assertFalse(check(cues, "badsha", result)["ok"])

    def test_review_and_take_reconciliation_gate(self):
        digest, cues, _ = load_srt(self.srt)
        result = propose(cues, digest)
        first = result["claims"][0]
        first.update(review_status="required", required=True,
                     linked_take_ids=["take-001"])
        for entry in result["claims"][1:]:
            entry.update(review_status="context", required=False)
        for entry in result["entities"]:
            entry.update(review_status="context")
        bad = check(cues, digest, result, takes=[], require_reviewed=True)
        self.assertFalse(bad["ok"])
        good = check(cues, digest, result,
                     takes=[{"id": "take-001", "claim_ids": [first["id"]]}],
                     require_reviewed=True)
        self.assertTrue(good["ok"])

    def test_cli_cannot_overwrite_existing_proposals(self):
        dest = self.root / "private-proposals"
        self.assertEqual(0, main(["propose", str(self.srt), "--output", str(dest)]))
        self.assertEqual(2, main(["propose", str(self.srt), "--output", str(dest)]))
        self.assertEqual(0, main(["check", str(self.srt), "--input", str(dest)]))
        self.assertEqual(1, main(["check", str(self.srt), "--input", str(dest),
                                  "--require-reviewed"]))


if __name__ == "__main__":
    unittest.main()
