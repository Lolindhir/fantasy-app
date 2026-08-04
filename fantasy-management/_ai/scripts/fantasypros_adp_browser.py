"""Headless-browser fallback for JavaScript-rendered FantasyPros ADP tables."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fantasypros_adp_html import (
    FantasyProsAdpError,
    find_ranking_table,
    parse_tables,
    table_diagnostics,
)

BROWSER_CANDIDATES = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
DEFAULT_VIRTUAL_TIME_BUDGET_MS = 20_000


def find_browser_executable() -> str:
    for candidate in BROWSER_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FantasyProsAdpError(
        "FantasyPros ADP browser fallback unavailable: no supported Chrome/Chromium executable found"
    )


def _run_browser(
    executable: str,
    url: str,
    *,
    timeout: int,
    virtual_time_budget_ms: int,
    profile_dir: Path,
    headless_flag: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        executable,
        headless_flag,
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-default-apps",
        "--disable-sync",
        "--hide-scrollbars",
        "--mute-audio",
        "--window-size=1920,1080",
        "--run-all-compositor-stages-before-draw",
        f"--virtual-time-budget={virtual_time_budget_ms}",
        f"--user-data-dir={profile_dir}",
        "--dump-dom",
        url,
    ]
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(timeout + 30, 60),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FantasyProsAdpError(
            f"FantasyPros ADP browser fallback timed out for {url}"
        ) from exc
    except OSError as exc:
        raise FantasyProsAdpError(
            f"FantasyPros ADP browser fallback could not start {executable}: {exc}"
        ) from exc


def render_adp_page_with_browser(
    url: str,
    *,
    timeout: int,
    virtual_time_budget_ms: int = DEFAULT_VIRTUAL_TIME_BUDGET_MS,
) -> tuple[str, dict[str, Any]]:
    """Render one public ADP page and require a trustworthy ranking table.

    GitHub-hosted Ubuntu runners include Chrome. The browser fallback is used
    only after the canonical HTML and official export both omit the ranking
    table. It does not relax any downstream identity, population or AVG checks.
    """
    if virtual_time_budget_ms < 1_000:
        raise ValueError("virtual_time_budget_ms must be at least 1000")

    executable = find_browser_executable()
    attempts: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="fantasypros-adp-browser-") as directory:
        profile_root = Path(directory)
        for index, headless_flag in enumerate(("--headless=new", "--headless"), start=1):
            profile_dir = profile_root / f"profile-{index}"
            result = _run_browser(
                executable,
                url,
                timeout=timeout,
                virtual_time_budget_ms=virtual_time_budget_ms,
                profile_dir=profile_dir,
                headless_flag=headless_flag,
            )
            html = result.stdout.strip()
            attempt: dict[str, Any] = {
                "headless_flag": headless_flag,
                "return_code": result.returncode,
                "rendered_bytes": len(result.stdout.encode("utf-8")),
                "stderr_tail": result.stderr[-2_000:],
            }
            if html:
                parsed = parse_tables(html)
                attempt["table_diagnostics"] = table_diagnostics(parsed)
                try:
                    find_ranking_table(parsed)
                except FantasyProsAdpError:
                    attempts.append(attempt)
                else:
                    return html, {
                        "browser_executable": executable,
                        "headless_flag": headless_flag,
                        "virtual_time_budget_ms": virtual_time_budget_ms,
                        "rendered_bytes": attempt["rendered_bytes"],
                        "attempt_count": index,
                    }
            else:
                attempts.append(attempt)

            # Retry only when the newer headless mode itself fails or returns a
            # DOM without the ranking table. The legacy flag is still supported
            # by older Chromium builds found outside GitHub-hosted runners.

    raise FantasyProsAdpError(
        "FantasyPros ADP browser-rendered page contained no ranking table: "
        f"url={url}; browser={executable}; attempts={attempts}"
    )
