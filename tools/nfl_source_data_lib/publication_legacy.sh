# NFL Source publication helpers, legacy behavior (Issue #1618 M2b.3).
# Source once before the retry loop; do not enable new routes or alter the
# existing guards/counters here. The workflow retains publication ownership.

clean_source_worktree() {
  git clean -fd -- data-source
}

assert_source_data_only() {
  mapfile -t changed < <(git status --porcelain=v1 | sed -E 's/^.. //')
  unexpected=()
  for path in "${changed[@]}"; do
    if [[ "$path" != data-source/* ]]; then
      unexpected+=("$path")
    fi
  done
  if (( ${#unexpected[@]} > 0 )); then
    printf 'Unexpected changes outside data-source/:\n' >&2
    printf ' - %s\n' "${unexpected[@]}" >&2
    return 1
  fi
}

assert_scoped_raw_write_set() {
  if [[ "$materialization_scope" != "injuries" ]]; then
    return 0
  fi
  mapfile -t changed < <(git status --porcelain=v1 --untracked-files=all | sed -E 's/^.. //')
  unexpected=()
  for path in "${changed[@]}"; do
    if [[ "$path" == "data-source/providers/nflverse/injuries/raw-${injury_year}.csv" ||
          "$path" == "data-source/providers/nflverse/injuries/metadata-${injury_year}.json" ||
          "$path" == "$failure_diagnostic_file" ]]; then
      continue
    fi
    unexpected+=("$path")
  done
  if (( ${#unexpected[@]} > 0 )); then
    printf 'Scoped injury Raw sync touched unexpected paths:\\n' >&2
    printf ' - %s\\n' "${unexpected[@]}" >&2
    return 1
  fi
}

assert_scoped_canonical_write_set() {
  if [[ "$materialization_scope" == "full" ]]; then
    return 0
  fi
  mapfile -t changed < <(git status --porcelain=v1 --untracked-files=all | sed -E 's/^.. //')
  unexpected=()
  for path in "${changed[@]}"; do
    if [[ "$materialization_scope" == "game-finality" ]]; then
      if [[ "$path" == data-source/nfl/schedules/* || "$path" == data-source/nfl/game-finality/* ]]; then
        continue
      fi
    elif [[ "$materialization_scope" == "schedule-odds" ]]; then
      if [[ "$path" == data-source/nfl/schedule-odds/* ]]; then
        continue
      fi
    elif [[ "$materialization_scope" == "injuries" ]]; then
      if [[ "$path" == data-source/nfl/injuries/"$injury_year"/* ]]; then
        continue
      fi
    fi
    if [[ "$path" == "$failure_diagnostic_file" ]]; then
      continue
    fi
    unexpected+=("$path")
  done
  if (( ${#unexpected[@]} > 0 )); then
    printf 'Scoped %s materialization touched unexpected paths:\n' "$materialization_scope" >&2
    printf ' - %s\n' "${unexpected[@]}" >&2
    return 1
  fi
}

assert_semantic_noop() {
  python - "$@" <<'PY'
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
scope = sys.argv[2]
if scope == "game-finality":
    expected = {
        "scheduleFilesChanged": 0,
        "scheduleChangedPaths": [],
        "gameFinalityFilesChanged": 0,
        "gameFinalityChangedPaths": [],
    }
elif scope == "schedule-odds":
    expected = {
        "oddsFilesChanged": 0,
        "oddsChangedPaths": [],
    }
elif scope == "injuries":
    expected = {
        "injuryCanonicalFilesChanged": 0,
        "injuryCanonicalChangedPaths": [],
        "injuryObsoleteRequiresReview": [],
    }
else:
    expected = {
        "identityChanged": False,
        "providerMappingsChanged": False,
        "draftFilesChanged": 0,
        "auditChanged": False,
    }
actual = {key: result.get(key) for key in expected}
if actual != expected:
    raise SystemExit(
        "Semantic no-op verification failed: "
        + json.dumps({"scope": scope, "expected": expected, "actual": actual}, sort_keys=True)
    )
PY
}
