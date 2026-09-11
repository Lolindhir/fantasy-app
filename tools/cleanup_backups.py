#!/usr/bin/env python3
"""Keep only the newest generated backup files per backup type."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path


BACKUP_DIR = Path("public/data/backup")
KEEP_PER_TYPE = 5


def backup_type(path: Path) -> str:
    return path.name.split("_", 1)[0]


def main() -> int:
    if not BACKUP_DIR.exists():
        print(f"Backup directory does not exist: {BACKUP_DIR}")
        return 0

    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in BACKUP_DIR.iterdir():
        if path.is_file():
            grouped[backup_type(path)].append(path)

    deleted = 0
    for kind, files in sorted(grouped.items()):
        ordered = sorted(files, key=lambda item: item.name)
        remove = ordered[:-KEEP_PER_TYPE] if len(ordered) > KEEP_PER_TYPE else []
        print(f"{kind}: {len(ordered)} backup(s), deleting {len(remove)}")
        for path in remove:
            print(f"Deleting {path}")
            path.unlink()
            deleted += 1

    print(f"Deleted {deleted} backup file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
