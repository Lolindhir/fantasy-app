"""Synthetic local semantic claim contract regressions; no podcast content."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from podcast_semantic_claims import serial, check, freeze, reconcile

SRT = """1
00:00:01,000 --> 00:00:06,000
Ferguson würde ich nicht starten. McBride klar davor.

2
00:00:06,000 --> 00:00:15,000
Die Defense bleibt gut. Ich bin skeptisch.
"""

class SemanticClaimsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "source.srt"
        self.source.write_text(SRT, encoding="utf-8")
        self.first = self.folder / "first.json"
        self.claim = {"id": "c1", "cue": 1, "start_offset": 0,
                      "end_offset": 33, "quote_hint": "Ferguson würde ich nicht starten.",
                      "kind": "start_sit", "claim": "Ferguson nicht starten",
                      "review_state": "unreviewed"}
        self.inventory = {"schema_version": 1,
                          "source_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                          "source_cue_range": [1, 2], "claims": [self.claim]}
        self.first.write_bytes(serial(self.inventory))

    def test_first_pass_is_frozen_and_audit_is_additive(self):
        folder = self.folder / "frozen"
        result = freeze(self.source, self.first, folder)
        audit = self.folder / "audit.json"
        audit.write_bytes(serial({
            "base_frozen_sha256": result["frozen_sha256"],
            "review_method": "second source read",
            "corrections": [{"id": "c1", "reason": "raw cue verified",
                             "review_state": "verified", "linked_take_ids": ["t1"]}],
            "new_claims": [{"id": "c2", "cue": 1, "start_offset": 34, "end_offset": 53,
                            "quote_hint": "McBride klar davor.", "kind": "comparison",
                            "claim": "McBride vor Ferguson", "review_state": "verified",
                            "linked_take_ids": ["t2"]}],
        }))
        out = self.folder / "reconciled"
        self.assertEqual(2, reconcile(self.source, folder, audit, out)["reconciled"])
        self.assertEqual(result["frozen_sha256"], hashlib.sha256((folder / "first-pass.json").read_bytes()).hexdigest())
        takes = self.folder / "takes.json"
        takes.write_bytes(serial([{"id": "t1", "claim_ids": ["c1"]}, {"id": "t2", "claim_ids": ["c2"]}]))
        self.assertTrue(check(self.source, out / "reconciled.json", require_reviewed=True, takes_path=takes)["ok"])

    def test_unreviewed_is_not_editorially_complete(self):
        self.assertTrue(check(self.source, self.first)["ok"])
        self.assertFalse(check(self.source, self.first, require_reviewed=True)["ok"])

    def test_reject_fabricated_quote_and_wrong_source_hash(self):
        self.inventory["claims"][0]["quote_hint"] = "Ferguson plays every snap"
        self.first.write_bytes(serial(self.inventory))
        with self.assertRaisesRegex(ValueError, "literal source span"):
            freeze(self.source, self.first, self.folder / "frozen")
        self.inventory["source_sha256"] = "0" * 64
        self.first.write_bytes(serial(self.inventory))
        with self.assertRaisesRegex(ValueError, "Source SHA256"):
            freeze(self.source, self.first, self.folder / "frozen")

    def test_reject_duplicate_id_and_wrong_audit_baseline(self):
        self.inventory["claims"].append(dict(self.claim))
        self.first.write_bytes(serial(self.inventory))
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            freeze(self.source, self.first, self.folder / "frozen")
        self.inventory["claims"] = [self.claim]
        self.first.write_bytes(serial(self.inventory))
        frozen = self.folder / "frozen"
        freeze(self.source, self.first, frozen)
        audit = self.folder / "audit.json"
        audit.write_bytes(serial({"base_frozen_sha256": "bad", "corrections": [], "new_claims": []}))
        with self.assertRaisesRegex(ValueError, "anchored"):
            reconcile(self.source, frozen, audit, self.folder / "out")

    def test_explicit_work_dir_claim_coverage_and_map_planning(self):
        work = self.folder / "work"
        items = work / "takes/items"
        items.mkdir(parents=True)
        map_path = work / "content-map/segments/s1.json"
        map_path.parent.mkdir(parents=True)
        map_manifest = {"segments": [{"segment_id": "s1", "path": "content-map/segments/s1.json"}]}
        (work / "content-map/manifest.json").write_bytes(serial(map_manifest))
        segment = {"segment_id": "s1", "substantive_claims": [{"claim_id": "c1"}],
                   "planned_outputs": {"take_ids": ["t1"]}}
        map_path.write_bytes(serial(segment))
        (items / "t1.json").write_bytes(serial({"id": "t1", "segment_ids": ["s1"], "claim_ids": ["c1"]}))
        self.claim.update(segment_id="s1", review_state="verified", linked_take_ids=["t1"])
        self.first.write_bytes(serial(self.inventory))
        self.assertTrue(check(self.source, self.first, require_reviewed=True, work_dir=work)["ok"])
        segment["planned_outputs"]["take_ids"] = []
        map_path.write_bytes(serial(segment))
        report = check(self.source, self.first, require_reviewed=True, work_dir=work)
        self.assertFalse(report["ok"])
        self.assertTrue(any("not planned" in e for e in report["errors"]))
        segment["planned_outputs"]["take_ids"] = ["t1"]
        segment["substantive_claims"] = []
        map_path.write_bytes(serial(segment))
        report = check(self.source, self.first, require_reviewed=True, work_dir=work)
        self.assertTrue(any("missing from Content Map" in e for e in report["errors"]))

    def test_context_only_needs_reason_and_unreviewed_blocks_source_qa(self):
        self.claim.update(segment_id="s1", review_state="context_only", review_note="")
        self.first.write_bytes(serial(self.inventory))
        self.assertFalse(check(self.source, self.first, require_reviewed=True)["ok"])
        self.claim["review_note"] = "Passing comparator only, no standalone take"
        self.first.write_bytes(serial(self.inventory))
        self.assertTrue(check(self.source, self.first, require_reviewed=True)["ok"])

    def test_cannot_rewrite_frozen_first_pass(self):
        frozen = self.folder / "frozen"
        freeze(self.source, self.first, frozen)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            freeze(self.source, self.first, frozen)
        (frozen / "first-pass.json").write_text("{}")
        audit = self.folder / "audit.json"
        audit.write_bytes(serial({"base_frozen_sha256": "bad", "corrections": [], "new_claims": []}))
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            reconcile(self.source, frozen, audit, self.folder / "out")

if __name__ == "__main__":
    unittest.main()
