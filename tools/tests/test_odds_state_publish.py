from __future__ import annotations

import base64
import copy
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from odds_state_publish import StatePublicationError, publish_state  # noqa: E402

GAME = "2026_07_TB_CAR"


def state(*, observed="2026-10-17T16:00:00Z", published="2026-10-17T15:00:00Z"):
    return {
        "SchemaVersion": 1, "Season": 2026,
        "Games": {GAME: {
            "PublishedFingerprint": "a" * 64,
            "PublishedAt": published,
            "ObservedAt": observed,
            "ObservedSpreadLine": 3.5,
            "ObservedTotalLine": 44.5,
            "PendingSince": "2026-10-17T16:00:00Z",
        }},
    }


def remote_body(data):
    return {
        "sha": "remote-blob-123",
        "content": base64.b64encode(
            json.dumps(data).encode("utf-8")
        ).decode("ascii"),
    }


class OddsStatePublisherTests(unittest.TestCase):
    def test_identical_semantic_state_makes_no_api_write(self):
        current = state()
        requests = []
        def call(method, path, body):
            requests.append((method, path, body))
            return 200, remote_body(current)
        self.assertEqual(publish_state(
            repository="Lolindhir/fantasy-app", season=2026,
            candidate=current, call=call,
        ), "noop")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], "GET")

    def test_cas_update_uses_remote_sha_and_never_main(self):
        requests = []
        def call(method, path, body):
            requests.append((method, path, body))
            if method == "GET":
                return 200, remote_body(state())
            return 200, {"content": {"sha": "new-blob"}}
        next_state = state(observed="2026-10-17T16:10:00Z")
        self.assertEqual(publish_state(
            repository="Lolindhir/fantasy-app", season=2026,
            candidate=next_state, call=call,
        ), "published")
        self.assertEqual(len(requests), 2)
        method, path, body = requests[1]
        self.assertEqual(method, "PUT")
        self.assertEqual(path, "/repos/Lolindhir/fantasy-app/contents/odds-buffer/2026.json")
        self.assertEqual(body["branch"], "odds-refresh-state")
        self.assertEqual(body["sha"], "remote-blob-123")
        self.assertEqual(json.loads(base64.b64decode(body["content"])), next_state)

    def test_stale_observation_or_checkpoint_is_rejected(self):
        newer = state(observed="2026-10-17T16:20:00Z")
        requests = []
        def call(method, path, body):
            requests.append(method)
            return 200, remote_body(newer)
        with self.assertRaisesRegex(StatePublicationError, "stale observer"):
            publish_state(repository="Lolindhir/fantasy-app", season=2026,
                          candidate=state(), call=call)
        self.assertEqual(requests, ["GET"])
        checkpoint_regression = state(
            observed="2026-10-17T16:30:00Z", published="2026-10-17T14:00:00Z"
        )
        with self.assertRaisesRegex(StatePublicationError, "checkpoint regressed"):
            publish_state(repository="Lolindhir/fantasy-app", season=2026,
                          candidate=checkpoint_regression, call=call)

    def test_concurrent_main_branch_race_or_auth_failure_fails_closed(self):
        for code in (403, 409, 422):
            with self.subTest(code=code):
                def call(method, path, body):
                    return (200, remote_body(state())) if method == "GET" else (code, {})
                with self.assertRaisesRegex(StatePublicationError, f"HTTP {code}"):
                    publish_state(repository="Lolindhir/fantasy-app", season=2026,
                                  candidate=state(observed="2026-10-17T16:10:00Z"),
                                  call=call)

    def test_bootstrap_requires_explicit_opt_in_and_existing_branch(self):
        events = []
        def call(method, path, body):
            events.append((method, path))
            if method == "GET" and "/contents/" in path:
                return 404, {}
            if method == "GET" and "/git/ref/" in path:
                return 200, {"object": {"sha": "branch-sha"}}
            return 201, {}
        with self.assertRaisesRegex(StatePublicationError, "explicitly bootstrap"):
            publish_state(repository="Lolindhir/fantasy-app", season=2026,
                          candidate=state(), call=call)
        self.assertEqual(publish_state(
            repository="Lolindhir/fantasy-app", season=2026,
            candidate=state(), call=call, bootstrap=True,
        ), "published")
        self.assertEqual(events[-1][0], "PUT")
        def missing_branch(method, path, body):
            return 404, {}
        with self.assertRaisesRegex(StatePublicationError, "branch is missing"):
            publish_state(repository="Lolindhir/fantasy-app", season=2026,
                          candidate=state(), call=missing_branch, bootstrap=True)

    def test_invalid_schema_rejected_before_any_api_access(self):
        broken = copy.deepcopy(state())
        broken["Games"][GAME]["PublishedFingerprint"] = "xyz"
        with self.assertRaises(StatePublicationError):
            publish_state(repository="Lolindhir/fantasy-app", season=2026,
                          candidate=broken,
                          call=lambda method, path, body: self.fail("Unexpected GitHub access"))


if __name__ == "__main__":
    unittest.main()
