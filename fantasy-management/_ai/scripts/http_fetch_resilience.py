#!/usr/bin/env python3
"""Compatibility shim: the bounded HTTP fetch helper lives in tools/external_source/http.py (Issue #988).

The fetchers under this directory move provider by provider into tools/external_source and drop
this shim with the last one.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.external_source import http as _impl  # noqa: E402

globals().update({name: value for name, value in vars(_impl).items() if not name.startswith("__")})
