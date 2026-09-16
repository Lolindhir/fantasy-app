from __future__ import annotations

import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import call, patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.acquire import fetch_sleeper_json  # noqa: E402


class _Response:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


class LeagueSourceSleeperFetchRetryTests(unittest.TestCase):
    def test_transient_url_error_recovers_with_bounded_backoff(self) -> None:
        error = urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))
        response = _Response(b'{"league_id":"123"}')

        with patch(
            "league_source_data_lib.acquire.urllib.request.urlopen",
            side_effect=[error, error, response],
        ) as urlopen, patch("league_source_data_lib.acquire.time.sleep") as sleep:
            payload = fetch_sleeper_json("https://api.sleeper.app/v1/league/123")

        self.assertEqual(payload, {"league_id": "123"})
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(1.0), call(3.0)])

    def test_retryable_http_error_recovers(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.sleeper.app/v1/league/123",
            503,
            "Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b""),
        )
        response = _Response(b"[]")

        with patch(
            "league_source_data_lib.acquire.urllib.request.urlopen",
            side_effect=[error, response],
        ) as urlopen, patch("league_source_data_lib.acquire.time.sleep") as sleep:
            payload = fetch_sleeper_json("https://api.sleeper.app/v1/league/123/users")

        self.assertEqual(payload, [])
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_non_retryable_http_error_fails_immediately(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.sleeper.app/v1/league/missing",
            404,
            "Not Found",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

        with patch(
            "league_source_data_lib.acquire.urllib.request.urlopen",
            side_effect=error,
        ) as urlopen, patch("league_source_data_lib.acquire.time.sleep") as sleep:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                fetch_sleeper_json("https://api.sleeper.app/v1/league/missing")

        self.assertEqual(raised.exception.code, 404)
        urlopen.assert_called_once()
        sleep.assert_not_called()

    def test_transient_failure_exhaustion_preserves_original_error(self) -> None:
        error = urllib.error.URLError(ConnectionResetError(104, "Connection reset by peer"))

        with patch(
            "league_source_data_lib.acquire.urllib.request.urlopen",
            side_effect=[error, error, error],
        ) as urlopen, patch("league_source_data_lib.acquire.time.sleep") as sleep:
            with self.assertRaises(urllib.error.URLError) as raised:
                fetch_sleeper_json("https://api.sleeper.app/v1/league/123")

        self.assertIs(raised.exception, error)
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(1.0), call(3.0)])

    def test_invalid_json_is_not_retried(self) -> None:
        response = _Response(b"not-json")

        with patch(
            "league_source_data_lib.acquire.urllib.request.urlopen",
            return_value=response,
        ) as urlopen, patch("league_source_data_lib.acquire.time.sleep") as sleep:
            with self.assertRaises(ValueError):
                fetch_sleeper_json("https://api.sleeper.app/v1/league/123")

        urlopen.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
