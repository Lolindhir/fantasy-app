#!/usr/bin/env bash
# Rebuilds every Fantasy Operations input dataset from the current checkout (Issue #947, S4 of #471).
#
# Generator command for tools/rebuild_and_publish.py in the `materialize` job of
# .github/workflows/fm-daily.yml: the helper resets the worktree to the latest main before every
# attempt, runs this script, validates that only fantasy-management/generated/operations changed
# and publishes the result. The script must therefore be deterministic and self-contained; the
# previous free-agent/movement snapshots are taken from the freshly reset worktree.
set -euo pipefail

RUNNER_TEMP="${RUNNER_TEMP:-$(mktemp -d)}"

previous_free_agent="$RUNNER_TEMP/free-agent-signals.previous.json"
previous_movement="$RUNNER_TEMP/free-agent-movement-signals.previous.json"
rm -f "$previous_free_agent" "$previous_movement"
if test -s fantasy-management/generated/operations/free-agent-signals.json; then
  cp fantasy-management/generated/operations/free-agent-signals.json "$previous_free_agent"
fi
if test -s fantasy-management/generated/operations/free-agent-movement-signals.json; then
  cp fantasy-management/generated/operations/free-agent-movement-signals.json "$previous_movement"
fi

python fantasy-management/_ai/scripts/build_source_freshness_gate.py
python fantasy-management/_ai/scripts/build_fantasy_operations_inputs.py
python fantasy-management/_ai/scripts/materialize_external_signals.py
python fantasy-management/_ai/scripts/build_player_signal_dataset.py --check
python fantasy-management/_ai/scripts/build_player_signal_dataset_with_projection_extensions.py
python fantasy-management/_ai/scripts/build_fa_board_readmodel.py
python fantasy-management/_ai/scripts/build_free_agent_dataset.py
if test -s "$previous_free_agent"; then
  python fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py --previous-free-agent-signals "$previous_free_agent"
else
  python fantasy-management/_ai/scripts/build_free_agent_movement_dataset.py
fi
if test -s "$previous_movement"; then
  python fantasy-management/_ai/scripts/build_free_agent_movement_events.py --previous-movement-signals "$previous_movement"
else
  python fantasy-management/_ai/scripts/build_free_agent_movement_events.py
fi
python fantasy-management/_ai/scripts/build_kicker_streaming_inputs.py

test -s fantasy-management/generated/operations/source-freshness.json || {
  echo "source-freshness.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/source-freshness.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/source-freshness-gate.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=data["population"]["source_count"]; assert count > 0 and len(data["sources"]) == count, "invalid source freshness population"; print("Validated source-freshness.json: status={}; fresh={}/{}; decision={}; no_event_conclusion_allowed={}.".format(data["overall_status"], data["population"]["fresh_count"], count, data["monitoring"]["decision"], data["monitoring"]["no_event_conclusion_allowed"]))'

test -s fantasy-management/generated/operations/player-signals.json || {
  echo "player-signals.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/player-signals.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/player-signal-dataset.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=data["population"]["player_count"]; assert count > 0 and len(data["players"]) == count, "invalid player-signals population"; print(f"Validated player-signals.json with {count} players.")'

test -s fantasy-management/generated/operations/fa-board-readmodel.json || {
  echo "fa-board-readmodel.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/fa-board-readmodel.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/fa-board-readmodel.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=data["population"]["player_count"]; assert count > 0 and len(data["players"]) == count, "invalid FA-board population"; assert data["quality"]["availability_fail_closed"] is True, "FA-board must be fail-closed"; print("Validated fa-board-readmodel.json with {} players; availability={}; draft={}; quality={}.".format(count, data["population"]["availability"], data["current_fa_draft"]["resolution_status"], data["quality"]["status"]))'

test -s fantasy-management/generated/operations/managed-roster-overview.json || {
  echo "managed-roster-overview.json is missing or empty after materialization" >&2
  exit 1
}
test -s fantasy-management/generated/operations/managed-roster-overview.md || {
  echo "managed-roster-overview.md is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/managed-roster-overview.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/managed-roster-overview.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=len(data["players"]); assert count > 0 and count == data["team"]["held_player_count"], "invalid managed roster overview population"; assert data["dataset_id"] == "managed-roster-overview", "invalid managed roster overview dataset id"; print("Validated managed-roster-overview.json with {} players; quality={}; unclassified={}.".format(count, data["quality"]["status"], data["evaluation"]["unclassified_count"]))'

test -s fantasy-management/generated/operations/free-agent-signals.json || {
  echo "free-agent-signals.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/free-agent-signals.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/free-agent-dataset.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=data["population"]["player_count"]; assert count > 0 and len(data["players"]) == count, "invalid free-agent-signals population"; assert all(player["ownership"]["status"] == "fantasy_free_agent" for player in data["players"]), "rostered player in free-agent-signals"; print(f"Validated free-agent-signals.json with {count} fantasy free agents.")'

test -s fantasy-management/generated/operations/free-agent-movement-signals.json || {
  echo "free-agent-movement-signals.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/free-agent-movement-signals.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/free-agent-movement-dataset.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); assert set(data["population"]["positions"]) == {"QB","RB","WR","TE","K"}, "movement population must include all fantasy positions"; assert len(data["discoveries"]) == data["population"]["discovery_count"], "invalid movement discovery count"; assert all(item["ownership"]["status"] == "fantasy_free_agent" for item in data["discoveries"]), "rostered player in movement discoveries"; print("Validated free-agent-movement-signals.json with {} discoveries from {} free agents; positions={}; priorities={}; families={}.".format(data["population"]["discovery_count"], data["population"]["free_agent_count"], data["population"]["discovery_position_counts"], data["population"]["priority_counts"], data["population"]["material_family_counts"]))'

test -s fantasy-management/generated/operations/free-agent-movement-events.json || {
  echo "free-agent-movement-events.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/free-agent-movement-events.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/free-agent-movement-events.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); assert set(data["population"]["positions"]) == {"QB","RB","WR","TE","K"}, "movement-event population must cover all fantasy positions"; assert len(data["events"]) == data["population"]["event_count"], "invalid movement-event count"; print("Validated free-agent-movement-events.json: baseline={}; current={}; previous={}; events={}; types={}; priorities={}.".format(data["population"]["baseline_mode"], data["population"]["current_discovery_count"], data["population"]["previous_discovery_count"], data["population"]["event_count"], data["population"]["event_type_counts"], data["population"]["event_priority_counts"]))'

test -s fantasy-management/generated/operations/kicker-streaming-inputs.json || {
  echo "kicker-streaming-inputs.json is missing or empty after materialization" >&2
  exit 1
}
python -c 'import json; from pathlib import Path; from jsonschema import Draft202012Validator; data=json.loads(Path("fantasy-management/generated/operations/kicker-streaming-inputs.json").read_text(encoding="utf-8")); schema=json.loads(Path("fantasy-management/_ai/schemas/kicker-streaming-inputs.schema.json").read_text(encoding="utf-8")); Draft202012Validator(schema).validate(data); count=data["population"]["candidate_count"]; held=data["population"]["held_count"]; free=data["population"]["free_agent_count"]; assert count > 0 and len(data["candidates"]) == count, "invalid kicker-streaming candidate population"; assert free > 0, "no fantasy-free-agent kickers in kicker-streaming inputs"; assert all(candidate["availability"] in {"held", "free_agent"} for candidate in data["candidates"]), "invalid kicker availability"; assert all(candidate["availability"] != "free_agent" or candidate["ownership"]["status"] == "fantasy_free_agent" for candidate in data["candidates"]), "rostered kicker marked free_agent"; print(f"Validated kicker-streaming-inputs.json with {count} candidates ({held} held, {free} free agents).")'
