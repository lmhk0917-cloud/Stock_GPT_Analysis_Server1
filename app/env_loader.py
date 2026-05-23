"""Load local .env files without external dependencies.

Only sets variables that are not already present in the process environment.
Secrets are never printed by this module.
"""

import os
from pathlib import Path


def load_project_env(project_root):
    root = Path(project_root)
    for filename in (".env.local", ".env"):
        path = root / filename
        if path.exists():
            _load_env_file(path)


def _load_env_file(path):
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
