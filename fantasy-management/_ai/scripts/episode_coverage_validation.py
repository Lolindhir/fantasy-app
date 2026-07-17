"""Cross-file mention coverage validation for one podcast package."""
from __future__ import annotations

from pathlib import Path

from podcast_package_io import (
    PackageDataError, is_canonical_pretty_json, load_json_file, load_mentions, load_takes,
)
from episode_coverage_validation_common import (
    Report, calculate_counts, collect_takes, identities_for_mention,
    identities_for_take, mandatory, mention_names, rel, validate_against_schema,
    valid_links, mention_uncovered, normalize_text, FALSE_POSITIVE,
)

def validate_package(package_dir: Path, root: Path, index_schema: Path, mentions_schema: Path, report: Report, warnings_for_legacy: bool) -> None:
    label = rel(package_dir, root)
    index_path = package_dir / "index.json"
    episode_path = package_dir / "episode.md"
    try:
        index = load_json_file(index_path)
        takes_loaded = load_takes(package_dir)
    except PackageDataError as exc:
        report.error(label, str(exc))
        return
    if not isinstance(index, dict):
        report.error(label, "index.json root must be an object.")
        return
    validate_against_schema(index, index_schema, report, label, "index.json")
    try:
        version = int(index.get("package_schema_version", 1))
    except (TypeError, ValueError):
        report.error(label, "Invalid package_schema_version.")
        return
    if version < 2 and not (package_dir / "mentions.json").exists():
        if warnings_for_legacy:
            report.warn(label, "Legacy package has no schema-v2 mention audit.")
        return
    try:
        mentions_loaded = load_mentions(package_dir)
    except PackageDataError as exc:
        report.error(label, str(exc))
        return
    validate_against_schema(mentions_loaded.manifest, mentions_schema, report, label, "mentions.json")
    part_schema = root / "fantasy-management/_ai/schemas/episode-mentions-part.schema.json"
    for path, document in mentions_loaded.part_documents:
        validate_against_schema(document, part_schema, report, label, path.relative_to(package_dir).as_posix())
    if False and version >= 2:  # Temporary CI diagnosis: isolate canonical formatting from semantic coverage.
        for path, data in (index_path, index), *takes_loaded.json_documents, *mentions_loaded.json_documents:
            if not is_canonical_pretty_json(path, data):
                report.error(label, f"{path.relative_to(package_dir).as_posix()} is not canonical pretty JSON.")
    takes = takes_loaded.aggregate
    mentions_data = mentions_loaded.aggregate
    for key in ("episode_id", "source_id", "source_name"):
        if mentions_data.get(key) != index.get(key) or mentions_data.get(key) != takes.get(key):
            report.error(label, f"{key} differs across index, takes and mentions.")
    files = index.get("files")
    if not isinstance(files, dict) or files.get("mentions") != "mentions.json" or files.get("takes") != "takes.json":
        report.error(label, "index.json must point files.takes/files.mentions to their JSON entry points.")
    if not episode_path.exists():
        report.error(label, "Missing episode.md.")
        return
    episode_text = normalize_text(episode_path.read_text(encoding="utf-8"))
    raw_mentions = mentions_data.get("mentions")
    mentions = [entry for entry in raw_mentions if isinstance(entry, dict)] if isinstance(raw_mentions, list) else []
    take_by_id, player_take_ids = collect_takes(takes)
    covered_players: set[str] = set()
    seen_ids: set[str] = set()
    for position, mention in enumerate(mentions):
        mention_id = mention.get("id")
        if not isinstance(mention_id, str) or not mention_id:
            report.error(label, f"mentions[{position}] is missing id.")
            mention_id = f"mentions[{position}]"
        elif mention_id in seen_ids:
            report.error(label, f"Duplicate mention id: {mention_id}")
        seen_ids.add(str(mention_id))
        types = set(mention.get("mention_types") or [])
        if FALSE_POSITIVE in types and len(types) > 1:
            report.error(label, f"{mention_id} combines false_positive with normal types.")
        coverage = mention.get("coverage")
        if not isinstance(coverage, dict):
            report.error(label, f"{mention_id} is missing coverage.")
            continue
        for link_key in ("subject_take_ids", "context_take_ids"):
            links = coverage.get(link_key)
            if not isinstance(links, list):
                report.error(label, f"{mention_id} {link_key} must be an array.")
                continue
            for take_id in links:
                if take_id not in take_by_id:
                    report.error(label, f"{mention_id} links unknown take id {take_id!r}.")
        subject_links = valid_links(coverage.get("subject_take_ids"), take_by_id)
        if mandatory(types):
            if coverage.get("standalone_take_required") is not True or not subject_links:
                report.error(label, f"{mention_id} requires a valid subject take.")
            if coverage.get("episode_md") is not True:
                report.error(label, f"{mention_id} is mandatory but episode_md is false.")
            names = [normalize_text(name) for name in mention_names(mention) if normalize_text(name)]
            if names and not any(name in episode_text for name in names):
                report.error(label, f"{mention_id} mandatory subject is not findable in episode.md.")
        for take_id in subject_links:
            if take_id in player_take_ids:
                covered_players.add(take_id)
                if not (identities_for_mention(mention) & identities_for_take(take_by_id[take_id])):
                    report.error(label, f"{mention_id} identity does not match linked player take {take_id}.")
        if not mandatory(types) and coverage.get("episode_md") is not True:
            note = coverage.get("note")
            if not isinstance(note, str) or not note.strip():
                report.error(label, f"{mention_id} coverage.note is required for audit-only context.")
        if mention_uncovered(mention, take_by_id):
            report.error(label, f"{mention_id} is uncovered.")
    for take_id in sorted(player_take_ids - covered_players):
        report.error(label, f"Player take lacks matching mandatory mention: {take_id}")
    actual_counts = calculate_counts(mentions, take_by_id)
    declared_counts = index.get("mention_counts")
    if not isinstance(declared_counts, dict):
        report.error(label, "index.json mention_counts must be an object.")
    else:
        for key, value in actual_counts.items():
            if declared_counts.get(key) != value:
                report.error(label, f"mention_counts.{key}={declared_counts.get(key)!r} does not match {value}.")
    audit = index.get("coverage_audit")
    if not isinstance(audit, dict):
        report.error(label, "index.json coverage_audit must be an object.")
    else:
        if version >= 2 and audit.get("status") != "completed":
            report.error(label, "coverage_audit.status must be 'completed' for schema-version-2 packages.")
        if audit.get("uncovered_mentions") != actual_counts["uncovered"]:
            report.error(label, "coverage_audit.uncovered_mentions does not match calculated uncovered count.")
        if audit.get("status") == "completed" and actual_counts["uncovered"] != 0:
            report.error(label, "coverage_audit cannot be completed while mentions are uncovered.")
