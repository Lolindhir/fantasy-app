"""Team abbreviation of a historical season (Issue #1621).

Python port of ``ConvertTo-TeamAbbreviation`` (public/requests/utils/league/TeamUtils.psm1), the rule that produces ``TeamAbbr`` of the
running season in League.json. The frontend derives no abbreviation; consumer generators call this so every season uses the same rule
with the team name of that season.
"""
from __future__ import annotations

STOP_WORDS = {"team", "the"}


def _is_number(char: str) -> bool:
    return char.isnumeric()


def _normalize(name: str) -> str:
    text = name.strip()
    # (\p{Lu}+)(\p{Lu}\p{Ll}) -> "$1 $2": a run of capitals followed by a lowercase letter splits before the last capital.
    out: list[str] = []
    for index, char in enumerate(text):
        if index >= 1 and index + 1 < len(text) and char.isupper() and text[index - 1].isupper() and text[index + 1].islower():
            out.append(" ")
        out.append(char)
    text = "".join(out)
    # ([\p{Ll}\p{N}])(\p{Lu}) -> "$1 $2"
    out = []
    for index, char in enumerate(text):
        if index >= 1 and char.isupper() and (text[index - 1].islower() or _is_number(text[index - 1])):
            out.append(" ")
        out.append(char)
    text = "".join(out)
    # [^\p{L}\p{N}]+ -> " "
    return "".join(char if char.isalpha() or _is_number(char) else " " for char in text).strip()


def team_abbreviation(team_name: str | None, team_id: int | str | None) -> str:
    try:
        fallback = f"T{int(str(team_id)):02d}"
    except (TypeError, ValueError):
        fallback = "TBD"
    if not team_name or not team_name.strip():
        return fallback
    normalized = _normalize(team_name)
    parts = [part for part in normalized.split() if part and part.lower() not in STOP_WORDS]
    if not parts:
        return fallback
    if len(parts) == 1:
        head = parts[0][:3]
        return head[0].upper() + head[1:].lower()
    if len(parts) == 2:
        prefix = parts[0][:2]
        return prefix[0].upper() + prefix[1:].lower() + parts[1][0].upper()
    return "".join(part[0].upper() for part in parts[:3])
