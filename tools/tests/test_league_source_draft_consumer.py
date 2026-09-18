import json
import tempfile
import unittest
from pathlib import Path
from tools.draft_canonical_consumer import build_legacy_payload

REPO_ROOT = Path(__file__).resolve().parents[2]

def project_draft(item):
    return {key: item.get(key) for key in ("season","status","type","start_time","settings","metadata","draft_order","slot_to_roster_id")}

def project_pick(item):
    return {key: item.get(key) for key in ("pick_no","player_id","roster_id","picked_by","metadata")}

def project_traded(item):
    return {key: item.get(key) for key in ("season","round","roster_id","previous_owner_id","owner_id")}

class DraftCanonicalConsumerTest(unittest.TestCase):
    def test_fixture_adapts_canonical_ids_to_sleeper_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); season_dir=root/"source-data"/"leagues"/"fixture"/"seasons"/"2026"; season_dir.mkdir(parents=True)
            (season_dir/"members.json").write_text(json.dumps([{"CanonicalLeagueMemberID":"m1","ProviderMappings":[{"Provider":"Sleeper","ProviderUserID":"u1"}]}]),encoding="utf-8")
            (season_dir/"rosters.json").write_text(json.dumps([{"CanonicalLeagueRosterID":"r1","ProviderMappings":[{"Provider":"Sleeper","ProviderRosterID":"1"}]}]),encoding="utf-8")
            (season_dir/"drafts.json").write_text(json.dumps([{
                "Season":2026,"Type":"linear","Status":"complete","StartTime":123,"Settings":{"rounds":1},"Metadata":{"name":"Fixture"},
                "ProviderMappings":[{"Provider":"Sleeper","ProviderDraftID":"d1"}],
                "DraftOrder":[{"CanonicalLeagueMemberID":"m1","Slot":1}],
                "SlotToRoster":[{"CanonicalLeagueRosterID":"r1","Slot":"1"}],
                "Picks":[{"PickNo":1,"CanonicalLeagueRosterID":"r1","PickedByCanonicalLeagueMemberID":"m1","Metadata":{"first_name":"Test","last_name":"Player"},"Player":{"ProviderMappings":[{"Provider":"Sleeper","ProviderPlayerID":"p1"}]}}],
                "TradedPicks":[{"Season":"2026","Round":1,"OriginalCanonicalLeagueRosterID":"r1","PreviousOwnerCanonicalLeagueRosterID":"r1","OwnerCanonicalLeagueRosterID":"r1"}]
            }]),encoding="utf-8")
            payload=build_legacy_payload(root,"fixture","2026")
            self.assertEqual(payload["Drafts"][0]["draft_order"],{"u1":1})
            self.assertEqual(payload["Drafts"][0]["slot_to_roster_id"],{"1":1})
            self.assertEqual(payload["PicksByDraftID"]["d1"][0]["player_id"],"p1")
            self.assertEqual(payload["PicksByDraftID"]["d1"][0]["picked_by"],"u1")
            self.assertEqual(payload["TradedPicksByDraftID"]["d1"][0]["roster_id"],1)

    def test_repository_adapter_matches_persisted_sleeper_raw_evidence(self):
        for season, expected_count in {"2024":1,"2025":1,"2026":2}.items():
            with self.subTest(season=season):
                payload=build_legacy_payload(REPO_ROOT,"nfl-reise",season)
                self.assertEqual(len(payload["Drafts"]),expected_count)
                for adapted in payload["Drafts"]:
                    draft_id=adapted["draft_id"]
                    matches=list((REPO_ROOT/"source-data"/"providers"/"sleeper"/"leagues").glob(f"*/drafts/{draft_id}"))
                    self.assertEqual(len(matches),1)
                    raw_dir=matches[0]
                    raw_draft=json.loads((raw_dir/"draft.json").read_text(encoding="utf-8"))
                    raw_picks=json.loads((raw_dir/"picks.json").read_text(encoding="utf-8"))
                    raw_traded=json.loads((raw_dir/"traded-picks.json").read_text(encoding="utf-8"))
                    self.assertEqual(project_draft(adapted),project_draft(raw_draft))
                    self.assertEqual([project_pick(x) for x in payload["PicksByDraftID"][draft_id]],[project_pick(x) for x in raw_picks])
                    sort_key=lambda x:(str(x["season"]),int(x["round"]),int(x["roster_id"]),int(x["previous_owner_id"]),int(x["owner_id"]))
                    self.assertEqual(sorted((project_traded(x) for x in payload["TradedPicksByDraftID"][draft_id]),key=sort_key),sorted((project_traded(x) for x in raw_traded),key=sort_key))

if __name__=="__main__":
    unittest.main()
