"""Shared implementation for the persistent NFL data-source layer."""

import sys
from pathlib import Path

# The shared data root definitions live in tools/data_roots.py; keep them importable when the package is
# loaded as ``tools.<package>`` from the repository root instead of with tools/ on sys.path.
_TOOLS_DIR = str(Path(__file__).resolve().parents[1])
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

