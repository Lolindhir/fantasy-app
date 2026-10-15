"""Temporary READ-ONLY all-final-weeks audit for #355; never merge this file.

Uses actual production source adapter, PowerShell slot bridge, scoring and
PWF parity checks, emits exact serialized generated data for 2026 W1-W4.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from team_week_performance import build_team_week_performance
from team_week_performance_materialize import verify_pwf_actual_parity
from team_week_performance_sources import load_verified_week_inputs

@unittest.skipUnless(shutil.which("pwsh"), "Real historical audit needs PowerShell")
class HistoricalAudit(unittest.TestCase):
    def test_all_scored_final_weeks_readonly(self) -> None:
        statuses = []
        for season, last in [(2024,17),(2025,17),(2026,5)]:
            for week in range(1, last+1):
                record = {"season": season, "week": week}
                try:
                    inputs = load_verified_week_inputs(ROOT,"nfl-reise",season,week)
                    model = build_team_week_performance(**inputs)
                    parity = verify_pwf_actual_parity(ROOT,model,inputs["matchup_rows"])
                    record.update(
                        status="ready",teams=len(model["Teams"]),
                        parity=parity, 
                        manager=max(t["PotentialPoints"] for t in model["Teams"]),
                        coach=max(t["EfficiencyPercent"] for t in model["Teams"]
                                  if t["EfficiencyPercent"] is not None),
                    )
                    if season==2026 and week<=4:
                        data=(json.dumps(model,ensure_ascii=False,sort_keys=True,
                              indent=2,allow_nan=False)+"\n").encode("utf-8")
                        digest=hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()
                        encoded=base64.b64encode(data).decode("ascii")
                        record["blobSha"]=digest
                        record["wireChars"]=len(encoded)
                        print("TWP_AUDIT_META="+json.dumps(record,sort_keys=True),flush=True)
                        for i in range(0,len(encoded),3000):
                            print(f"TWP_AUDIT_PART_{season}_{week:02d}="+encoded[i:i+3000],flush=True)
                except Exception as exc:
                    record.update(status="blocked",reason=f"{type(exc).__name__}: {exc}"[:600])
                statuses.append(record)
                print("TWP_AUDIT_WEEK="+json.dumps(record,sort_keys=True),flush=True)
        print("TWP_AUDIT_SUMMARY="+json.dumps(statuses,sort_keys=True),flush=True)
        self.assertEqual(len(statuses),39)
        self.assertTrue(any(r["season"]==2026 and r["week"]==5
                            and r["status"]=="ready" for r in statuses))

if __name__ == "__main__":
    unittest.main()
