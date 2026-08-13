"""Environment loading for LLM credentials.

Loads a local ``.env`` file (repo root) into ``os.environ`` without
overriding already-set environment variables.  No external dependency
(python-dotenv is intentionally avoided to keep the runtime minimal).

Secrets never leave this module: only ``os.environ`` values are consumed,
and ``.env`` is gitignored.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path | None = None) -> bool:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Existing environment variables take precedence (no override).
    Returns True if a file was loaded.
    """
    dotenv_path = Path(path) if path else _default_dotenv_path()
    if dotenv_path is None or not dotenv_path.exists():
        return False

    loaded = False
    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if key not in os.environ:
            os.environ[key] = value
            loaded = True
    return loaded


def _default_dotenv_path() -> Path | None:
    """Locate the repo-root .env file (project root relative to this file)."""
    here = Path(__file__).resolve()
    # src/aftbench/llm/env.py -> repo root is 4 parents up
    root = here.parents[3]
    candidate = root / ".env"
    return candidate if candidate.exists() else None


def get_secret(name: str) -> str | None:
    """Return a secret from the environment (after .env load), or None."""
    load_dotenv()
    return os.environ.get(name)
