#!/usr/bin/env python3
"""Bounded HTTP text fetching for automated external-source collectors."""

from __future__ import annotations

import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, Sequence

DEFAULT_RETRYABLE_HTTP_STATUS = frozenset({403, 408, 425, 429, 500, 502, 503, 504})
DEFAULT_RETRY_DELAYS_SECONDS = (10.0, 30.0, 60.0)
MAX_RETRY_AFTER_SECONDS = 120.0
MAX_ERROR_BODY_BYTES = 512
MAX_ERROR_EXCERPT_CHARS = 300


class HttpFetchError(RuntimeError):
    """Raised when a bounded external HTTP fetch cannot complete safely."""


def _retry_after_seconds(headers: Any) -> float | None:
    if not headers:
        return None
    value = headers.get("Retry-After")
    if not value:
        return None
    value = str(value).strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds()
    return min(MAX_RETRY_AFTER_SECONDS, max(0.0, seconds))


def _retry_delay(
    retry_index: int,
    retry_delays: Sequence[float],
    *,
    headers: Any = None,
) -> float:
    base_delay = float(retry_delays[retry_index])
    retry_after = _retry_after_seconds(headers)
    if retry_after is not None:
        base_delay = max(base_delay, retry_after)
    return base_delay + random.uniform(0.0, 1.0)


def _error_excerpt(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read(MAX_ERROR_BODY_BYTES)
    except (OSError, ValueError):
        return ""
    if not raw:
        return ""
    charset = "utf-8"
    try:
        charset = exc.headers.get_content_charset() or charset
    except AttributeError:
        pass
    text = raw.decode(charset, errors="replace")
    return " ".join(text.split())[:MAX_ERROR_EXCERPT_CHARS]


def fetch_text_with_retry(
    url: str,
    *,
    timeout: int = 30,
    headers: Mapping[str, str] | None = None,
    source_name: str = "External source",
    retry_delays: Sequence[float] = DEFAULT_RETRY_DELAYS_SECONDS,
    retryable_http_status: frozenset[int] = DEFAULT_RETRYABLE_HTTP_STATUS,
) -> tuple[str, dict[str, str]]:
    """Fetch UTF-8-compatible text with bounded retries for transient failures."""

    request_headers = dict(headers or {})
    attempts = len(retry_delays) + 1
    for attempt_index in range(attempts):
        request = urllib.request.Request(url, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
                return body, {
                    "etag": response.headers.get("ETag") or "",
                    "last_modified": response.headers.get("Last-Modified") or "",
                    "content_type": response.headers.get("Content-Type") or "",
                }
        except urllib.error.HTTPError as exc:
            can_retry = exc.code in retryable_http_status and attempt_index < len(retry_delays)
            if can_retry:
                delay = _retry_delay(attempt_index, retry_delays, headers=exc.headers)
                exc.close()
                time.sleep(delay)
                continue
            excerpt = _error_excerpt(exc)
            detail = f"status={exc.code} reason={exc.reason}"
            if excerpt:
                detail += f" body_excerpt={excerpt!r}"
            raise HttpFetchError(
                f"{source_name} fetch failed after {attempt_index + 1} attempt(s): {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt_index < len(retry_delays):
                time.sleep(_retry_delay(attempt_index, retry_delays))
                continue
            raise HttpFetchError(
                f"{source_name} fetch failed after {attempt_index + 1} attempt(s): {exc}"
            ) from exc

    raise AssertionError("bounded HTTP retry loop exited unexpectedly")
