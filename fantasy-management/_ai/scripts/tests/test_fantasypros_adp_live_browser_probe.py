"""Temporary PR-only ChromeDriver diagnostic for live FantasyPros ADP controls."""

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

BRANCH = "agent/fix-fantasypros-adp-browser-render"
PPR_URL = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return handle.getsockname()[1]


def request_json(base, method, path, payload=None, timeout=30):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


class Driver:
    def __enter__(self):
        executable = shutil.which("chromedriver")
        if not executable:
            raise RuntimeError("chromedriver not found")
        port = free_port()
        self.base = f"http://127.0.0.1:{port}"
        self.session = ""
        self.process = subprocess.Popen(
            [executable, f"--port={port}", "--allowed-ips="],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                if request_json(self.base, "GET", "/status", timeout=2).get("value", {}).get("ready"):
                    break
            except Exception:
                time.sleep(0.25)
        created = request_json(
            self.base,
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
                                "--window-size=1920,1080",
                            ]
                        },
                    }
                }
            },
        )
        self.session = created.get("value", {}).get("sessionId", "")
        if not self.session:
            raise RuntimeError(f"could not create ChromeDriver session: {created}")
        return self

    def command(self, method, suffix, payload=None, timeout=45):
        return request_json(
            self.base,
            method,
            f"/session/{self.session}{suffix}",
            payload,
            timeout,
        ).get("value")

    def __exit__(self, *_):
        try:
            if self.session:
                self.command("DELETE", "", timeout=5)
        except Exception:
            pass
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except Exception:
                pass


SCRIPT = r"""
const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
const attrs = element => Object.fromEntries(Array.from(element?.attributes ?? []).map(attr => [attr.name, attr.value]));
const describe = element => element ? {
  tag: element.tagName,
  text: clean(element.innerText || element.textContent).slice(0, 1000),
  href: element.href || '',
  className: element.className || '',
  id: element.id || '',
  attributes: attrs(element),
} : null;
const table = document.querySelector('table.mcu-table') || document.querySelector('table');
const ancestors = [];
let current = table;
for (let depth = 0; current && depth < 7; depth++, current = current.parentElement) {
  ancestors.push({
    depth,
    tag: current.tagName,
    id: current.id || '',
    className: current.className || '',
    attributes: attrs(current),
    textTail: clean(current.innerText || current.textContent).slice(-2000),
    childTags: Array.from(current.children).map(child => ({tag: child.tagName, id: child.id || '', className: child.className || '', text: clean(child.innerText || child.textContent).slice(0, 300)})).slice(0, 30),
  });
}
const interesting = Array.from(document.querySelectorAll('a,button,[role="button"],select,input'))
  .map(describe)
  .filter(item => /more|all|next|load|view|unlock|premium|subscribe|sign|export|download|page|rank|adp/i.test(`${item.text} ${item.href} ${item.className} ${JSON.stringify(item.attributes)}`))
  .slice(0, 150);
const forms = Array.from(document.forms).map(form => ({
  action: form.action,
  method: form.method,
  id: form.id,
  className: form.className,
  controls: Array.from(form.elements).map(control => describe(control)).slice(0, 50),
})).slice(0, 30);
const tableHtml = table?.parentElement?.parentElement?.outerHTML || table?.outerHTML || '';
const scripts = Array.from(document.scripts).map((script, index) => ({
  index,
  src: script.src || '',
  type: script.type || '',
  length: script.textContent?.length || 0,
  hasTopPlayer: /Jahmyr Gibbs|Bijan Robinson/.test(script.textContent || ''),
  hasRankMarkers: /rank_ave|adpData|player_name|mcu-table|reports__table/i.test(script.textContent || ''),
  matchingContext: (() => {
    const text = script.textContent || '';
    const match = text.search(/Jahmyr Gibbs|rank_ave|adpData|player_name|reports__table/i);
    return match >= 0 ? clean(text.slice(Math.max(0, match - 300), match + 1000)) : '';
  })(),
})).filter(item => item.hasTopPlayer || item.hasRankMarkers || /adp|rank|report|table/i.test(item.src)).slice(0, 80);
return {
  url: location.href,
  title: document.title,
  tableRows: table?.tBodies[0]?.rows.length ?? null,
  tableAttributes: attrs(table),
  ancestors,
  interesting,
  forms,
  tableHtmlLength: tableHtml.length,
  tableHtmlPrefix: clean(tableHtml).slice(0, 12000),
  tableHtmlSuffix: clean(tableHtml).slice(-6000),
  scripts,
};
"""


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_HEAD_REF") == BRANCH,
    "temporary live probe",
)
class LiveControlsProbe(unittest.TestCase):
    def test_inspect_controls_around_public_adp_table(self):
        with Driver() as driver:
            driver.command("POST", "/url", {"url": PPR_URL})
            time.sleep(12)
            diagnostic = driver.command(
                "POST", "/execute/sync", {"script": SCRIPT, "args": []}
            )
            self.fail("FantasyPros ADP controls diagnostic: " + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
