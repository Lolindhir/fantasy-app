"""Temporary PR-only ChromeDriver diagnostic for live FantasyPros ADP pages."""

import json
import os
import shutil
import signal
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone

BRANCH = "agent/fix-fantasypros-adp-browser-render"
PPR_URL = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return handle.getsockname()[1]


def http_json(base_url, method, path, payload=None, timeout=20):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


class ChromeDriverSession:
    def __init__(self):
        self.process = None
        self.base_url = ""
        self.session_id = ""
        self.driver_log = ""

    def __enter__(self):
        executable = shutil.which("chromedriver")
        if not executable:
            raise RuntimeError("chromedriver not found on GitHub runner")
        port = free_port()
        self.base_url = f"http://127.0.0.1:{port}"
        self.process = subprocess.Popen(
            [executable, f"--port={port}", "--allowed-ips="],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                status = http_json(self.base_url, "GET", "/status", timeout=2)
                if status.get("value", {}).get("ready"):
                    break
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
                time.sleep(0.25)
        else:
            raise RuntimeError("chromedriver did not become ready")

        created = http_json(
            self.base_url,
            "POST",
            "/session",
            {
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "chrome",
                        "pageLoadStrategy": "eager",
                        "goog:chromeOptions": {
                            "args": [
                                "--headless=new",
                                "--no-sandbox",
                                "--disable-dev-shm-usage",
                                "--disable-gpu",
                                "--disable-extensions",
                                "--disable-default-apps",
                                "--disable-sync",
                                "--hide-scrollbars",
                                "--mute-audio",
                                "--window-size=1920,1080",
                            ]
                        },
                    }
                }
            },
            timeout=30,
        )
        value = created.get("value", {})
        self.session_id = value.get("sessionId") or created.get("sessionId") or ""
        if not self.session_id:
            raise RuntimeError(f"chromedriver session creation failed: {created}")
        return self

    def command(self, method, suffix, payload=None, timeout=30):
        return http_json(
            self.base_url,
            method,
            f"/session/{self.session_id}{suffix}",
            payload,
            timeout=timeout,
        ).get("value")

    def navigate(self, url):
        self.command("POST", "/url", {"url": url}, timeout=45)

    def execute(self, script):
        return self.command(
            "POST", "/execute/sync", {"script": script, "args": []}, timeout=30
        )

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.session_id:
                self.command("DELETE", "", timeout=5)
        except Exception:
            pass
        if self.process is not None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except Exception:
                    pass
            if self.process.stdout is not None:
                try:
                    self.driver_log = self.process.stdout.read()[-4000:]
                except Exception:
                    self.driver_log = ""


DIAGNOSTIC_SCRIPT = r"""
const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
const tables = Array.from(document.querySelectorAll('table')).map((table, index) => {
  let dataTable = null;
  let isDataTable = false;
  let pageInfo = null;
  let dataLength = null;
  let settings = null;
  try {
    if (window.jQuery && jQuery.fn && jQuery.fn.dataTable && jQuery.fn.dataTable.isDataTable(table)) {
      isDataTable = true;
      dataTable = jQuery(table).DataTable();
      pageInfo = dataTable.page.info();
      dataLength = dataTable.rows().data().length;
      const rawSettings = dataTable.settings()[0];
      settings = {
        displayLength: rawSettings?._iDisplayLength ?? null,
        displayStart: rawSettings?._iDisplayStart ?? null,
        recordsTotal: rawSettings?.fnRecordsTotal ? rawSettings.fnRecordsTotal() : null,
        recordsDisplay: rawSettings?.fnRecordsDisplay ? rawSettings.fnRecordsDisplay() : null,
        serverSide: rawSettings?.oFeatures?.bServerSide ?? null,
        deferRender: rawSettings?.oFeatures?.bDeferRender ?? null,
        scroller: Boolean(rawSettings?.oScroller),
        ajaxSource: rawSettings?.sAjaxSource ?? rawSettings?.ajax ?? null,
        columns: Array.from(rawSettings?.aoColumns ?? []).map(column => ({
          title: clean(column.sTitle),
          data: typeof column.mData === 'string' ? column.mData : typeof column.mData,
          name: clean(column.sName),
        })),
      };
    }
  } catch (error) {
    settings = {error: clean(error)};
  }
  return {
    index,
    id: table.id,
    className: table.className,
    bodyRowCount: table.tBodies[0]?.rows.length ?? 0,
    totalDomRowCount: table.rows.length,
    headers: Array.from(table.querySelectorAll('thead th')).map(cell => clean(cell.innerText || cell.textContent)),
    firstRows: Array.from(table.querySelectorAll('tbody tr')).slice(0, 8).map(row =>
      Array.from(row.cells).map(cell => clean(cell.innerText || cell.textContent))
    ),
    isDataTable,
    pageInfo,
    dataLength,
    settings,
  };
});

const candidates = [];
const inspectArray = (owner, key, value) => {
  if (!Array.isArray(value) || value.length < 20) return;
  const first = value.find(item => item && typeof item === 'object');
  candidates.push({
    owner,
    key,
    length: value.length,
    firstKeys: first ? Object.keys(first).slice(0, 60) : [],
  });
};
for (const key of Object.keys(window)) {
  if (candidates.length >= 100) break;
  let value;
  try { value = window[key]; } catch (_) { continue; }
  inspectArray('window', key, value);
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    for (const nestedKey of ['players', 'data', 'rankings', 'rows', 'items', 'aaData']) {
      try { inspectArray(key, nestedKey, value[nestedKey]); } catch (_) {}
    }
  }
}

const resources = performance.getEntriesByType('resource')
  .map(entry => entry.name)
  .filter(name => /adp|rank|player|ajax|api|json|data/i.test(name))
  .slice(0, 150);

return {
  readyState: document.readyState,
  title: document.title,
  url: location.href,
  bodyTextPrefix: clean(document.body?.innerText).slice(0, 1500),
  tables,
  candidates,
  resources,
  windowKeys: Object.keys(window).filter(key => /adp|rank|player|data|draft/i.test(key)).slice(0, 200),
  jqueryVersion: window.jQuery?.fn?.jquery ?? null,
  dataTablesVersion: window.jQuery?.fn?.dataTable?.version ?? null,
  timestamp: new Date().toISOString(),
};
"""


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("GITHUB_HEAD_REF") == BRANCH,
    "temporary live probe runs only on its dedicated pull-request branch",
)
class FantasyProsAdpLiveBrowserProbe(unittest.TestCase):
    def test_inspect_current_ppr_data_model(self):
        with ChromeDriverSession() as driver:
            driver.navigate(PPR_URL)
            time.sleep(15)
            diagnostic = driver.execute(DIAGNOSTIC_SCRIPT)
            self.fail(
                "FantasyPros ADP ChromeDriver diagnostic: "
                + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)
            )


if __name__ == "__main__":
    unittest.main()
