"""AC6A diagnostic: classify attempted data opens in Python processes.

Test/audit tooling only, not a production dependency or a security sandbox.
Python's open audit event fires before the operation: a read attempt is not
proof that the file existed or its contents affected a calculation. Rules
identify reviewed call sites, not data flow. Native reads, fd-only access,
stat/listing operations, and non-Python executables require separate evidence.
Use isolated scratch roots; the trace never changes a publisher or model.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_roots import (
    DATA_CANONICAL_ROOT, DATA_DERIVED_ROOT, DATA_META_ROOT, DATA_SOURCE_ROOT,
)

CODE_ROOT = Path(__file__).resolve().parents[1]
ROOTS = {
    "source": Path(DATA_SOURCE_ROOT),
    "canonical": Path(DATA_CANONICAL_ROOT),
    "derived": Path(DATA_DERIVED_ROOT),
    "meta": Path(DATA_META_ROOT),
    "app": Path("public", "data"),
}
ROLES = frozenset({"input", "comparison", "delivery"})
_ENV_ROOT = "FORECAST_TRACE_ROOT"
_ENV_LOG = "FORECAST_TRACE_LOG"


class TraceError(ValueError):
    """Missing, ambiguous, forbidden or incompletely captured evidence."""


@dataclass(frozen=True)
class ReadRule:
    id: str
    root: str
    pattern: str
    reader: str
    caller: str | None
    role: str
    note: str

    def matches(self, event: dict[str, Any]) -> bool:
        if event["root"] != self.root:
            return False
        path, pattern = event["path"].split("/"), self.pattern.split("/")
        if len(path) != len(pattern):
            return False
        if not all(fnmatch.fnmatchcase(p, g) for p, g in zip(path, pattern)):
            return False
        sites = event["sites"]
        return bool(sites and sites[0] == self.reader
                    and (self.caller is None or sites[1:2] == [self.caller]))


def load_rules(path: Path) -> tuple[ReadRule, ...]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schemaVersion") != 1 or not isinstance(document.get("rules"), list):
        raise TraceError("Unsupported read manifest")
    rules = tuple(ReadRule(**row) for row in document["rules"])
    ids = set()
    for rule in rules:
        if (not rule.id or rule.id in ids or rule.root not in ROOTS
                or rule.role not in ROLES or not rule.reader or not rule.note
                or "**" in rule.pattern or any(part in {"", ".", ".."}
                    for part in rule.pattern.split("/"))):
            raise TraceError(f"Invalid or duplicate read rule: {rule}")
        ids.add(rule.id)
    return rules


def classify_reads(
    events: list[dict[str, Any]], rules: tuple[ReadRule, ...], *,
    own_product: str | None = None,
) -> list[dict[str, Any]]:
    """Require one reviewed rule per attempted read, with a producer guard.

    For a producer stage, declare its own Derived product. Neither App output
    nor that product's previous output may supply a computation input. A
    separate delivery stage may read the persisted Derived document. Scope
    own_product to the currently rebuilt product/partition in later stages;
    do not use this helper to permit undeclared earlier-phase reads.
    """
    classified = []
    for event in events:
        if event["kind"] == "violation":
            raise TraceError(f"Blocked data access (even if caller caught the exception): {event}")
        if event["kind"] != "open" or not event["read"]:
            continue
        matches = [rule for rule in rules if rule.matches(event)]
        if len(matches) != 1:
            raise TraceError(f"Expected one read rule, got {len(matches)}: {event}")
        rule = matches[0]
        own = (own_product is not None and event["root"] == "derived"
               and event["path"].split("/")[0] == own_product)
        if ((event["root"] == "app" and rule.role == "input")
                or (own and rule.role != "comparison")
                or (own_product is not None and event["root"] == "app"
                    and rule.role != "comparison")):
            raise TraceError(f"Forbidden producer feedback: {rule.id}: {event}")
        if own_product is not None and rule.role == "delivery":
            raise TraceError(f"Delivery read in producer stage: {rule.id}: {event}")
        classified.append({**event, "rule": rule.id, "role": rule.role})
    return classified


def _data_path(root: Path, value: Any) -> tuple[str, str] | None:
    if not isinstance(value, (str, bytes)):
        return None  # fd-only open has no path in this audit event
    path = Path(os.path.abspath(os.fsdecode(value)))
    for name, prefix in ROOTS.items():
        try:
            relative = path.relative_to(root / prefix)
        except ValueError:
            continue
        return name, relative.as_posix()
    return None


def _reader_sites() -> list[str]:
    sites = []
    frame = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        if not filename.startswith("<"):
            path = Path(os.path.abspath(filename))
            if path != Path(__file__).resolve():
                try:
                    relative = path.relative_to(CODE_ROOT)
                except ValueError:
                    pass
                else:
                    sites.append(f"{relative.as_posix()}:{frame.f_code.co_name}")
        frame = frame.f_back
    return sites


def install_from_environment() -> None:
    """Called from a temporary sitecustomize in a traced Python process."""
    root = Path(os.environ[_ENV_ROOT])
    fd = os.open(os.environ[_ENV_LOG], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    pid = os.getpid()

    def emit(event: dict[str, Any]) -> None:
        data = (json.dumps({"pid": pid, **event}, separators=(",", ":")) + "\n").encode()
        if os.write(fd, data) != len(data):
            raise TraceError("Incomplete trace record")

    def blocked(message: str, value: Any) -> None:
        emit({"kind": "violation", "message": message,
              "path": os.fsdecode(value), "sites": _reader_sites()})
        raise TraceError(f"{message}: {value}")

    def guard_path(value: Any, *, write: bool) -> None:
        # Keep traced Python data operations inside the scratch namespace.
        # Linked upstream roots are read-only; never follow them for writes.
        if _data_path(CODE_ROOT, value) is not None:
            blocked("Direct checkout data access outside scratch namespace", value)
        scoped = _data_path(root, value)
        if write and scoped is not None:
            target = Path(os.path.abspath(os.fsdecode(value)))
            if (scoped[0] not in {"derived", "app"}
                    or not target.resolve().is_relative_to(root)):
                blocked("Write outside writable scratch data", value)

    def hook(event: str, args: tuple[Any, ...]) -> None:
        if event == "subprocess.Popen":
            executable = os.path.basename(os.fsdecode(args[0])).lower()
            python = bool(re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?(?:\.exe)?", executable))
            emit({"kind": "spawn", "python": python, "executable": executable})
        elif event == "open":
            flags = args[2]
            access = flags & os.O_ACCMODE
            fresh = (flags & os.O_CREAT) and (flags & os.O_EXCL)
            read = access != os.O_WRONLY and not fresh and not (flags & os.O_TRUNC)
            write = access != os.O_RDONLY or bool(flags & (os.O_CREAT | os.O_TRUNC))
            guard_path(args[0], write=write)
            scoped = _data_path(root, args[0])
            if scoped is None:
                return
            emit({"kind": "open", "root": scoped[0], "path": scoped[1],
                  "read": bool(read), "write": write, "sites": _reader_sites()})
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.truncate", "os.utime"}:
            guard_path(args[0], write=True)
        elif event in {"os.rename", "os.link"}:
            guard_path(args[0], write=True)
            guard_path(args[1], write=True)
        elif event == "os.symlink":
            guard_path(args[1], write=True)

    sys.addaudithook(hook)
    emit({"kind": "start", "parent": os.getppid()})


@dataclass
class TraceRun:
    process: subprocess.CompletedProcess[str]
    events: list[dict[str, Any]]

    @property
    def processes(self) -> int:
        return sum(event["kind"] == "start" for event in self.events)


def trace_python(root: Path, args: list[str], *, timeout: float = 120) -> TraceRun:
    """Trace one Python command and inherited Python subprocesses.

    Startup receipts detect missing instrumentation on ordinary Popen Python
    children (including -S/-I). Non-Python Popen children fail this Python-only
    gate rather than masquerade as covered. An independent native/PowerShell
    boundary audit is still required. The caller checks expected exit status,
    output contents and actual writes; a successful trace alone proves none.
    """
    root = root.resolve()
    if (not root.is_dir() or root == CODE_ROOT or root in CODE_ROOT.parents
            or CODE_ROOT in root.parents):
        raise TraceError("Trace requires an isolated scratch root outside the checkout")
    with tempfile.TemporaryDirectory(prefix="forecast-trace-") as directory:
        bootstrap = Path(directory)
        log = bootstrap / "events.jsonl"
        (bootstrap / "sitecustomize.py").write_text(
            "from forecast_dependency_trace import install_from_environment\n"
            "install_from_environment()\n", encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env[_ENV_ROOT], env[_ENV_LOG] = str(root), str(log)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(bootstrap), str(CODE_ROOT / "tools")]
            + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        process = subprocess.run([sys.executable, *args], cwd=root, env=env,
                                 capture_output=True, text=True, timeout=timeout)
        events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.is_file() else []
    starts = [event for event in events if event["kind"] == "start"]
    spawns = [event for event in events if event["kind"] == "spawn"]
    pids = {event["pid"] for event in starts}
    if (any(not event["python"] for event in spawns) or len(starts) != 1 + len(spawns)
            or len(pids) != len(starts) or any(event["pid"] not in pids for event in events)):
        raise TraceError(f"Uncovered Python subprocess boundary: starts={starts}, spawns={spawns}; {process.stderr}")
    return TraceRun(process, events)
