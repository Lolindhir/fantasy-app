#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def grep(pattern: str) -> list[str]:
    result = subprocess.run(
        ["git", "grep", "-n", "-E", pattern],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    return [line for line in result.stdout.splitlines() if line]


# Safety: the helper functions being removed must not have external consumers.
helper_pattern = r"Get-FantasyRosteredPlayerIds|Get-PlayerPointHistoryMetrics|Test-PlayerHistoricalProduction|Get-PlayerRelevantReasons|Get-RelevantPlayers|Get-NumberOrZero"
external_helper_refs = [
    line for line in grep(helper_pattern)
    if not line.startswith("public/requests/utils/player/PlayerUtils.psm1:")
    and not line.startswith("public/requests/RequestLeague.ps1:")
]
if external_helper_refs:
    raise RuntimeError("Unexpected external relevant-player helper references:\n" + "\n".join(external_helper_refs))

# RequestLeague: keep Players.json consumption for salary-cap calculation, remove AI/chat helper production.
path = "public/requests/RequestLeague.ps1"
text = read(path)
text = replace_once(
    text,
    '    Import-Module "$PSScriptRoot\\utils\\player\\PlayerUtils.psm1" -ErrorAction Stop -Force\n    Import-Module "$PSScriptRoot\\utils\\player\\PlayerChatExportUtils.psm1" -ErrorAction Stop -Force\n',
    '    Import-Module "$PSScriptRoot\\utils\\player\\PlayerUtils.psm1" -ErrorAction Stop -Force\n',
    "RequestLeague import",
)
text = replace_once(
    text,
    '# Dateinamen\n$ScheduleFile = $config.ScheduleFile\n$PlayersRelevantFile = $config.PlayersRelevantFile\n$PlayersRelevantChatDir = $config.PlayersRelevantChatDir\n',
    '# Dateinamen\n$ScheduleFile = $config.ScheduleFile\n',
    "RequestLeague config variables",
)
text = replace_once(
    text,
    '    # --- Alle Spieler holen (für Salary Cap Berechnung und relevante Spielerdatei) ---\n',
    '    # --- Alle Spieler holen (für Salary Cap Berechnung) ---\n',
    "RequestLeague player comment",
)
text = replace_once(
    text,
    '''    # --- Relevante Spielerdatei schreiben ---\n    $relevantPlayers = Get-RelevantPlayers -Players $playersData -Teams $teamData\n    $comparePlayers = {\n        param($oldPlayers, $newPlayers)\n        Compare-Players -OldPlayers $oldPlayers -NewPlayers $newPlayers\n    }\n    Save-JsonFile -TargetFile $PlayersRelevantFile -Data $relevantPlayers -CompareScript $comparePlayers\n\n    Export-PlayersForChatChunks `\n    -Players $relevantPlayers `\n    -TargetDirectory $PlayersRelevantChatDir `\n    -ChunkSize 10 `\n    -Source "Players_Relevant.json"\n\n''',
    '',
    "RequestLeague relevant-player output block",
)
write(path, text)

# ConfigUtils: remove obsolete technical paths.
path = "public/requests/utils/ConfigUtils.psm1"
text = read(path)
text = replace_once(
    text,
    '    $PlayersFile = Join-Path $DataDir "Players.json"\n    $PlayersRelevantFile = Join-Path $DataDir "Players_Relevant.json"\n    $PlayersRelevantChatDir = Join-Path $DataDir "chat\\players-relevant"\n',
    '    $PlayersFile = Join-Path $DataDir "Players.json"\n',
    "ConfigUtils path definitions",
)
text = replace_once(
    text,
    '        PlayersFile                      = $PlayersFile\n        PlayersRelevantFile              = $PlayersRelevantFile\n        PlayersRelevantChatDir           = $PlayersRelevantChatDir\n',
    '        PlayersFile                      = $PlayersFile\n',
    "ConfigUtils returned paths",
)
write(path, text)

# PlayerUtils: all functions from Get-NumberOrZero onward belong exclusively to the retired relevant-player filter.
path = "public/requests/utils/player/PlayerUtils.psm1"
text = read(path)
marker = "function Get-NumberOrZero {"
if text.count(marker) != 1:
    raise RuntimeError("PlayerUtils: expected one relevant-helper block marker")
text = text[: text.index(marker)].rstrip() + "\n"
write(path, text)

# Generated commit labels: no longer classify retired outputs.
path = ".github/scripts/Invoke-GeneratedDataCommit.ps1"
text = read(path)
text = replace_once(text, '        "^public/data/chat/players-relevant/" { return "Player chat export" }\n', '', "commit helper chat label")
text = replace_once(text, '        "/Players_Relevant\\.json$" { return "Relevant players" }\n', '', "commit helper relevant label")
write(path, text)

# Fantasy Management source guidance: canonical raw Players + FM-derived operational contracts replace chat chunks.
path = "fantasy-management/_ai/FANTASY_MANAGEMENT_SOURCES.md"
text = read(path)
text = text.replace('- `public/data/chat/players-relevant/index.json`\n', '')
text = text.replace('- `public/data/chat/players-relevant/players_*.json`\n', '')
player_section_pattern = re.compile(r"## Player source rules\n.*?(?=### Sleeper player metadata and nominal depth-chart fields)", re.S)
replacement = '''## Player source rules\n\n`public/data/Players.json` is the canonical current raw player read model from the application context. Fantasy Management consumes it read-only and must not require the app producer to create AI- or agent-specific reduced copies or chunk exports.\n\nFor broad operational analysis, prefer the smallest current Fantasy-Management-owned derived contract that matches the task instead of scanning the raw player file:\n\n1. `fantasy-management/generated/operations/player-signals.json` for the league-wide QB/RB/WR/TE/K operational population and joined market, projection, activity, ownership, injury and nominal-role signals.\n2. `fantasy-management/generated/operations/free-agent-signals.json` for the complete current fantasy-free-agent population.\n3. `fantasy-management/generated/operations/managed-roster-signals.json` for Mighty Giants roster-focused work.\n\nWhen a raw app field or an exact player record is needed, read the targeted current record from `public/data/Players.json`. Do not recreate `Players_Relevant.json` or a chunked chat export merely to make the player data easier for a specific AI client to ingest.\n\nImportant player fields may include ID, name fields, NFL team, position, age, salary, projected salary, status, injury fields, games played/potential, snaps, attempts, fantasy points, point history, game history, ranking, grading, FantasyPros and ESPN fields, plus `ESPNID`, `SleeperDepthChartPosition` and `SleeperDepthChartOrder` when present.\n\n'''
text, count = player_section_pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"FANTASY_MANAGEMENT_SOURCES player section: expected one match, found {count}")
write(path, text)

# Durable cross-context guidance: client-specific convenience exports belong to the consumer, not the canonical app producer.
path = ".ai-context/manual/ai-guidance.yaml"
text = read(path)
anchor = "    - When Fantasy Management needs additional freshness, observability or monitoring evidence for app data, implement it in an independent Fantasy-Management-owned path that consumes published app state rather than injecting a dependency into the app producer.\n"
new_rule = "    - Do not make canonical app producers generate reduced, chunked or duplicated datasets solely for a particular AI, chat or agent client's ingestion limits; use targeted reads or consumer-owned derived contracts instead.\n"
if new_rule not in text:
    text = replace_once(text, anchor, anchor + new_rule, "AI guidance consumer-export rule")
write(path, text)

# ADR-015 remains historical but is superseded by the retirement decision.
path = ".ai-context/manual/decisions.yaml"
text = read(path)
adr015_anchor = "  - id: ADR-015\n    title: Relevant player chat export is generated helper output\n    status: accepted\n"
adr015_replacement = "  - id: ADR-015\n    title: Relevant player chat export is generated helper output\n    status: superseded\n    supersededBy: ADR-024\n"
text = replace_once(text, adr015_anchor, adr015_replacement, "ADR-015 status")
if "  - id: ADR-024\n" in text:
    raise RuntimeError("ADR-024 already exists; choose a new decision id before publishing")
adr024 = '''\n  - id: ADR-024\n    title: Retire app-generated AI player subsets and chat chunks\n    status: accepted\n    context: >\n      Players_Relevant.json and its ten-player chat chunks were introduced to work\n      around an earlier AI-client ingestion limit. Fantasy Operations now has\n      consumer-owned derived contracts for broad player analysis, while targeted\n      repository reads can retrieve exact raw player records without requiring a\n      duplicated app-generated player dataset.\n    decision: >\n      Keep public/data/Players.json as the canonical current raw player read model.\n      Remove public/data/Players_Relevant.json, public/data/chat/players-relevant/**\n      and their app-generation helpers. Fantasy Management should use its own\n      derived Operations contracts for broad analysis and targeted read-only access\n      to Players.json when raw player fields are required. Canonical app producers\n      must not generate reduced, chunked or duplicated datasets solely for an AI,\n      chat or agent client's ingestion limits.\n    rationale: >\n      Tool-specific convenience outputs are consumer concerns. Removing them keeps\n      the application producer independent from Fantasy Management and avoids\n      frequent League refresh churn across dozens of files that have no app\n      consumer.\n    consequences:\n      positive:\n        - RequestLeague no longer filters and republishes an AI-only player subset.\n        - The 10-minute League refresh no longer rewrites chat chunk artifacts.\n        - Fantasy Management relies on canonical app inputs and FM-owned derived contracts.\n        - There is no second relevance definition competing with player-signals population rules.\n      negative:\n        - Agents needing a raw field outside an FM-derived contract must perform a targeted Players.json read.\n'''
text = text.rstrip() + "\n" + adr024
write(path, text)

# Remove obsolete implementation and generated outputs.
for file_path in [
    ROOT / "public/requests/utils/player/PlayerChatExportUtils.psm1",
    ROOT / "public/data/Players_Relevant.json",
]:
    if file_path.exists():
        file_path.unlink()
chat_dir = ROOT / "public/data/chat/players-relevant"
if chat_dir.exists():
    shutil.rmtree(chat_dir)

# No productive references to the retired implementation/output may remain.
stale_pattern = r"Players_Relevant|public/data/chat/players-relevant|PlayerChatExportUtils|PlayersRelevantFile|PlayersRelevantChatDir|Get-RelevantPlayers|Export-PlayersForChatChunks|Player chat export"
stale = []
for line in grep(stale_pattern):
    # ADR-015/ADR-024 intentionally preserve historical names and explain the retirement.
    if line.startswith(".ai-context/manual/decisions.yaml:"):
        continue
    if line.startswith(".github/scripts/remove-relevant-player-chat-export.py:"):
        continue
    stale.append(line)
if stale:
    raise RuntimeError("Unexpected stale Relevant Players references remain:\n" + "\n".join(stale))

print("Relevant-player chat export cleanup prepared successfully.")
