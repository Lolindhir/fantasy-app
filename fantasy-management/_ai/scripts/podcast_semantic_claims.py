"""Local claim-inventory checkpoint. Does not infer claims or prove recall/audio fidelity."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from podcast_preflight import load_srt, _take_files

STATES = {"unreviewed", "verified", "needs_review", "context_only"}

def serial(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(value):
    return hashlib.sha256(value).hexdigest()

def validate(source, inventory, *, require_reviewed=False):
    digest, cues, _ = load_srt(source)
    errors = []
    if not isinstance(inventory, dict):
        return ["Inventory must be a JSON object"]
    if inventory.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if inventory.get("source_sha256") != digest:
        errors.append("Source SHA256 mismatch")
    bounds = inventory.get("source_cue_range")
    known = {cue["cue"]: cue for cue in cues}
    if (not isinstance(bounds, list) or len(bounds) != 2 or
        any(type(n) is not int for n in bounds) or
        bounds[0] > bounds[1] or bounds[0] not in known or bounds[1] not in known):
        errors.append("Invalid source_cue_range")
        bounds = None
    claims = inventory.get("claims")
    if not isinstance(claims, list) or not claims:
        return errors + ["Inventory must have at least one claim"]
    seen = set()
    for index, claim in enumerate(claims):
        label = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{label}: not an object")
            continue
        ident = claim.get("id")
        if not isinstance(ident, str) or not ident:
            errors.append(f"{label}: empty ID")
        elif ident in seen:
            errors.append(f"{label}: duplicate ID")
        else:
            seen.add(ident)
        if not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
            errors.append(f"{label}: empty paraphrase")
        if not isinstance(claim.get("kind"), str) or not claim["kind"].strip():
            errors.append(f"{label}: missing kind")
        state = claim.get("review_state")
        if state not in STATES:
            errors.append(f"{label}: invalid/missing review_state")
        if require_reviewed and state not in {"verified", "context_only"}:
            errors.append(f"{label}: outstanding editorial review")
        if state == "context_only" and not str(claim.get("review_note") or "").strip():
            errors.append(f"{label}: context-only exclusion needs reason")
        cue_num = claim.get("cue")
        cue = known.get(cue_num) if type(cue_num) is int else None
        if cue is None:
            errors.append(f"{label}: missing source cue")
            continue
        if bounds and not bounds[0] <= cue_num <= bounds[1]:
            errors.append(f"{label}: source cue outside declared range")
        start, end = claim.get("start_offset"), claim.get("end_offset")
        if (type(start) is not int or type(end) is not int or
            start < 0 or end <= start or end > len(cue["text"])):
            errors.append(f"{label}: invalid character offsets")
            continue
        quote = claim.get("quote_hint")
        if not isinstance(quote, str) or not quote.strip() or quote not in cue["text"][start:end]:
            errors.append(f"{label}: quote_hint is not a literal source span")
        links = claim.get("linked_take_ids", [])
        if not isinstance(links, list) or any(not isinstance(t, str) or not t for t in links):
            errors.append(f"{label}: invalid linked_take_ids")
        elif len(links) != len(set(links)):
            errors.append(f"{label}: duplicate take link")
    return errors

def ensure_empty(output):
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Refusing to overwrite non-empty output directory")
    output.mkdir(parents=True, exist_ok=True)

def freeze(source, proposal, output):
    if output.resolve() in {source.resolve(), proposal.resolve()}:
        raise ValueError("Output may not replace input")
    data = read(proposal)
    errors = validate(source, data)
    if errors:
        raise ValueError("; ".join(errors))
    if any(c.get("review_state") != "unreviewed" for c in data["claims"]):
        raise ValueError("First-pass baseline must be unreviewed; apply reviews in second pass")
    snapshot = serial(data)
    ensure_empty(output)
    (output / "first-pass.json").write_bytes(snapshot)
    (output / "first-pass.sha256").write_text(sha(snapshot) + "\n", encoding="ascii")
    return {"claims": len(data["claims"]), "frozen_sha256": sha(snapshot)}

def load_frozen(directory):
    snapshot = (directory / "first-pass.json").read_bytes()
    expected = (directory / "first-pass.sha256").read_text(encoding="ascii").strip()
    digest = sha(snapshot)
    if expected != digest:
        raise ValueError("Frozen first-pass SHA256 mismatch (snapshot changed)")
    return json.loads(snapshot), digest

def reconcile(source, frozen, audit_path, output):
    original, frozen_sha = load_frozen(frozen)
    errors = validate(source, original)
    if errors:
        raise ValueError("Invalid frozen input: " + "; ".join(errors))
    audit = read(audit_path)
    if not isinstance(audit, dict) or audit.get("base_frozen_sha256") != frozen_sha:
        raise ValueError("Audit is not anchored to frozen SHA256")
    fixes = audit.get("corrections", [])
    additions = audit.get("new_claims", [])
    if not isinstance(fixes, list) or not isinstance(additions, list):
        raise ValueError("Audit corrections/new_claims must be arrays")
    out = json.loads(json.dumps(original))
    by_id = {item["id"]: item for item in out["claims"]}
    seen = set()
    for fix in fixes:
        if not isinstance(fix, dict) or fix.get("id") not in by_id or fix["id"] in seen:
            raise ValueError("Invalid/duplicate correction ID")
        seen.add(fix["id"])
        if not isinstance(fix.get("reason"), str) or not fix["reason"].strip():
            raise ValueError("Every correction needs an explanation")
        if set(fix) - {"id", "reason", "review_state", "corrected_claim", "review_note", "linked_take_ids"}:
            raise ValueError("Cannot silently edit evidence/other fields")
        item = by_id[fix["id"]]
        if "corrected_claim" in fix:
            item["claim"] = fix["corrected_claim"]
        for key in ("review_state", "review_note", "linked_take_ids"):
            if key in fix:
                item[key] = fix[key]
        item["audit_reason"] = fix["reason"]
    for new in additions:
        if not isinstance(new, dict) or not isinstance(new.get("id"), str) or new["id"] in by_id:
            raise ValueError("Invalid/duplicate new claim")
        out["claims"].append(new)
        by_id[new["id"]] = new
    out["base_frozen_sha256"] = frozen_sha
    out["review_method"] = audit.get("review_method", "unspecified")
    errors = validate(source, out)
    if errors:
        raise ValueError("Invalid reconciliation: " + "; ".join(errors))
    if output.resolve() in {source.resolve(), audit_path.resolve(), frozen.resolve()}:
        raise ValueError("Output must not replace inputs")
    ensure_empty(output)
    (output / "reconciled.json").write_bytes(serial(out))
    (output / "audit.json").write_bytes(serial(audit))
    return {"first_pass": len(original["claims"]), "added": len(additions),
            "corrections": len(fixes), "reconciled": len(out["claims"])}

def check(source, inventory_path, *, require_reviewed=False, takes_path=None):
    inventory = read(inventory_path)
    errors = validate(source, inventory, require_reviewed=require_reviewed)
    if takes_path is not None:
        takes = _take_files(takes_path)
        index = {take.get("id"): take for take in takes if isinstance(take, dict)}
        if len(index) != len(takes):
            errors.append("Duplicate/missing take IDs")
        for claim in inventory.get("claims", []):
            links = claim.get("linked_take_ids", [])
            if require_reviewed and claim.get("review_state") == "verified" and not links:
                errors.append(f"{claim['id']}: reviewed substantive claim has no take link")
            for take_id in links:
                take = index.get(take_id)
                if take is None or claim["id"] not in take.get("claim_ids", []):
                    errors.append(f"{claim['id']}: take {take_id} missing reciprocal claim_id")
    claims = inventory.get("claims", [])
    return {"ok": not errors, "claims": len(claims),
            "editorially_reviewed": sum(c.get("review_state") in {"verified", "context_only"} for c in claims),
            "errors": errors, "semantic_recall_proven": False}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("srt", type=Path); f.add_argument("inventory", type=Path)
    f.add_argument("--output", required=True, type=Path)
    r = sub.add_parser("reconcile")
    r.add_argument("srt", type=Path); r.add_argument("frozen", type=Path)
    r.add_argument("audit", type=Path); r.add_argument("--output", required=True, type=Path)
    c = sub.add_parser("check")
    c.add_argument("srt", type=Path); c.add_argument("inventory", type=Path)
    c.add_argument("--require-reviewed", action="store_true")
    c.add_argument("--takes", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "freeze":
            result = freeze(args.srt, args.inventory, args.output)
        elif args.cmd == "reconcile":
            result = reconcile(args.srt, args.frozen, args.audit, args.output)
        else:
            result = check(args.srt, args.inventory, require_reviewed=args.require_reviewed, takes_path=args.takes)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("ok", True) else 1
    except (ValueError, OSError, UnicodeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Semantic claim preflight: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
