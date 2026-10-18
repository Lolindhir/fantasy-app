"""Bounded, review-first podcast preflight. Never claims exhaustive semantic extraction.

CLI:
  python podcast_preflight.py propose path/to/transcript.srt --output /private/path
  python podcast_preflight.py check path/to/transcript.srt --input /private/path [--takes /private/takes] [--require-reviewed]
No external services, source uploads, or repository writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CUE_TIME = re.compile(r"^\d{2}:\d{2}:\d{2}[,.]\d{3}$")
NAME_TOKEN = r"(?:[A-ZÄÖÜ]\.){2,}|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’-]*"
CAPITALIZED = re.compile(rf"\b(?:{NAME_TOKEN})(?:[ \t]+(?:{NAME_TOKEN})){{0,2}}")
CLAIM_PATTERN = re.compile(
    r"\b(?:start(?:en|et|e)?|sit(?:ten)?|bench|flex|rank(?:ing|ed)?|"
    r"(?:QB|RB|WR|TE)\s*[-#]?\s*\d{1,3}|besser|schlechter|vor|über|"
    r"lieber|würde|sollte|muss|nicht spielen|aufstellen|"
    r"Trade|traden|kaufen|verkaufen|waiver|stream(?:en|er|ing)?|"
    r"Verletzung|verletzt|concussion|out|questionable|"
    r"Targets?|Snaps?|Carries|Touches|Blitz|Pressure|Defense|"
    r"Offensive.Line|Matchup|Punkte|Touchdown|gewinnen|"
    r"Over.Under|O.Line|Bye|verfügbar|gesund|schonen|Einsatz|"
    r"ausfallen|spielt|spielen|könnte|vielleicht|sollten|Aufstellung)\b",
    re.I,
)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")


def parse_srt(text: str) -> list[dict]:
    """Preserve exact cue text; reject incomplete, duplicate or malformed cue ranges."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    blocks = re.split(r"\n[ \t]*\n", normalized.strip())
    cues = []
    ids = set()
    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 3 or not lines[0].strip().isdigit() or " --> " not in lines[1]:
            raise ValueError("Invalid SRT cue header; expected index, timing and text.")
        ident = int(lines[0].strip())
        start, end = lines[1].split(" --> ", 1)
        if not (CUE_TIME.fullmatch(start.strip()) and CUE_TIME.fullmatch(end.strip())):
            raise ValueError(f"Malformed time for cue {ident}")
        if ident in ids or not "\n".join(lines[2:]).strip():
            raise ValueError(f"Duplicate or empty SRT cue {ident}")
        ids.add(ident)
        cues.append({"cue": ident, "start": start.strip(), "end": end.strip(),
                     "text": "\n".join(lines[2:])})
    if not cues:
        raise ValueError("No cues")
    if sorted(ids) != list(range(min(ids), max(ids) + 1)):
        raise ValueError("SRT cue ids must be contiguous.")
    return cues


def load_srt(path: Path) -> tuple[str, list[dict], str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    return hashlib.sha256(raw).hexdigest(), parse_srt(text), text


def fingerprint(prefix: str, cue: int, offset: int) -> str:
    return f"{prefix}-{cue:05d}-{offset:05d}"


def propose(cues: list[dict], digest: str, start: int | None = None,
            end: int | None = None) -> dict:
    selected = [cue for cue in cues
                if (start is None or cue["cue"] >= start) and
                (end is None or cue["cue"] <= end)]
    if not selected:
        raise ValueError("No cues in requested selection.")
    entities, claims = [], []
    for cue in selected:
        body = cue["text"]
        for match in CAPITALIZED.finditer(body):
            entities.append({
                "id": fingerprint("entity", cue["cue"], match.start()),
                "cue": cue["cue"], "start_offset": match.start(),
                "end_offset": match.end(), "raw": match.group(),
                "candidate_kind": "unknown", "review_status": "unreviewed",
                "canonical_entity": None,
            })
        spans = []
        cursor = 0
        for boundary in SENTENCE_BOUNDARY.finditer(body):
            spans.append((cursor, boundary.start()))
            cursor = boundary.end()
        spans.append((cursor, len(body)))
        for left, right in spans:
            snippet = body[left:right]
            if not CLAIM_PATTERN.search(snippet):
                continue
            # Candidate sentences are pointers, not adjudicated atomic claims.
            first = len(snippet) - len(snippet.lstrip())
            last = len(snippet.rstrip())
            if last <= first:
                continue
            lo, hi = left + first, left + last
            claims.append({
                "id": fingerprint("claim", cue["cue"], lo),
                "cue": cue["cue"], "start_offset": lo, "end_offset": hi,
                "raw": body[lo:hi], "review_status": "unreviewed",
                "required": None, "linked_take_ids": [],
            })
    return {
        "manifest": {
            "schema_version": 1, "source_sha256": digest,
            "cue_count": len(selected), "cue_first": selected[0]["cue"],
            "cue_last": selected[-1]["cue"],
            "review_state": "unreviewed",
            "limitations": [
                "Heuristic high-recall candidate PROPOSALS, not exhaustive NER or claim extraction.",
                "German nouns may be false positives; lowercase/ASR names may be missed.",
                "Claim sentences may combine multiple obligations or miss unstated patterns.",
                "An independent human/LLM source inventory and QA remain mandatory.",
            ],
        },
        "entities": entities,
        "claims": claims,
    }


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _take_files(root: Path) -> list[dict]:
    if root.is_file():
        obj = load(root)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict) and isinstance(obj.get("takes"), list):
            return obj["takes"]
        raise ValueError("Take input must be a list or {'takes': [...]} JSON.")
    files = sorted(root.glob("*.json"))
    if not files:
        raise ValueError("No take JSON files found.")
    return [load(path) for path in files]


def check(cues: list[dict], digest: str, data: dict,
          takes: list[dict] | None = None, require_reviewed: bool = False) -> dict:
    issues = []
    manifest = data.get("manifest", {})
    if manifest.get("source_sha256") != digest:
        issues.append("Transcript SHA256 differs from inventory manifest.")
    by_id = {cue["cue"]: cue for cue in cues}
    if not all(k in data for k in ("entities", "claims")):
        issues.append("Missing inventory sections.")
    all_ids = set()
    candidate_count = 0
    unreviewed = 0
    for kind in ("entities", "claims"):
        for entry in data.get(kind, []):
            candidate_count += 1
            ident = entry.get("id")
            if ident in all_ids:
                issues.append(f"Duplicate candidate id: {ident}")
            all_ids.add(ident)
            cue = by_id.get(entry.get("cue"))
            if cue is None:
                issues.append(f"{ident}: unknown source cue")
                continue
            lo, hi = entry.get("start_offset"), entry.get("end_offset")
            if not isinstance(lo, int) or not isinstance(hi, int) or lo < 0 or hi <= lo:
                issues.append(f"{ident}: invalid offsets")
                continue
            if cue["text"][lo:hi] != entry.get("raw"):
                issues.append(f"{ident}: raw text is not an exact source span")
            if entry.get("review_status") not in ("unreviewed", "required", "context", "false_positive", "needs_review"):
                issues.append(f"{ident}: unknown review_status")
            if entry.get("review_status") == "unreviewed":
                unreviewed += 1
            if require_reviewed and entry.get("review_status") in ("unreviewed", None):
                issues.append(f"{ident}: not reviewed")
    takes_by_id = {take["id"]: take for take in (takes or []) if "id" in take}
    if takes is not None and len(takes_by_id) != len(takes):
        issues.append("Duplicate or missing take ID.")
    required = 0
    for claim in data.get("claims", []):
        if claim.get("required") is not True:
            continue
        required += 1
        linked = claim.get("linked_take_ids", [])
        if not linked:
            issues.append(f"{claim.get('id')}: required claim has no take link")
        if takes is None:
            continue
        for take_id in linked:
            take = takes_by_id.get(take_id)
            if take is None:
                issues.append(f"{claim.get('id')}: linked take {take_id} missing")
            elif claim.get("id") not in take.get("claim_ids", []):
                issues.append(f"{claim.get('id')}: {take_id} lacks reciprocal claim_id")
    if require_reviewed:
        for claim in data.get("claims", []):
            if claim.get("required") is None:
                issues.append(f"{claim.get('id')}: required/context classification missing")
        if takes is None:
            issues.append("--require-reviewed needs --takes for cross-check.")
    return {"ok": not issues, "errors": issues, "candidate_total": candidate_count,
            "unreviewed": unreviewed, "required_claims": required,
            "checked_take_count": len(takes_by_id)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose", help="Generate preliminary raw-cue candidates")
    p.add_argument("srt", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start-cue", type=int)
    p.add_argument("--end-cue", type=int)
    q = sub.add_parser("check", help="Check exact spans and reviewed claim/take links")
    q.add_argument("srt", type=Path)
    q.add_argument("--input", type=Path, required=True)
    q.add_argument("--takes", type=Path)
    q.add_argument("--require-reviewed", action="store_true")
    args = parser.parse_args(argv)
    try:
        digest, cues, _ = load_srt(args.srt)
        if args.command == "propose":
            if args.output.resolve() == args.srt.resolve() or args.output.suffix:
                raise ValueError("--output must be an output DIRECTORY, never the SRT itself")
            data = propose(cues, digest, args.start_cue, args.end_cue)
            if args.output.exists() and any(args.output.iterdir()):
                raise ValueError("Refusing to overwrite a non-empty proposal directory")
            args.output.mkdir(parents=True, exist_ok=True)
            for name in ("manifest", "entities", "claims"):
                dump(args.output / f"{name}.json", data[name])
            print(json.dumps({"cues": data["manifest"]["cue_count"],
                              "entity_candidates": len(data["entities"]),
                              "claim_candidates": len(data["claims"]),
                              "output": str(args.output)}, ensure_ascii=False))
            return 0
        data = {key: load(args.input / f"{key}.json")
                for key in ("manifest", "entities", "claims")}
        result = check(cues, digest, data, _take_files(args.takes) if args.takes else None,
                       args.require_reviewed)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"preflight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
