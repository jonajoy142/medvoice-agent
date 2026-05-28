from __future__ import annotations

import subprocess
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _run_backend(args: list[str]) -> None:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("POETRY_ACTIVE", None)
    try:
        raise SystemExit(subprocess.call(["poetry", "run", *args], cwd=BACKEND, env=env))
    except KeyboardInterrupt:
        raise SystemExit(130)


def backend_dev() -> None:
    _run_backend(["uvicorn", "app.main:app", "--reload"])


def backend_test() -> None:
    _run_backend(["pytest", "-q"])


def backend_migrate() -> None:
    _run_backend(["alembic", "upgrade", "head"])


def uvicorn_proxy() -> None:
    """Compatibility wrapper for `poetry run uvicorn app.main:app ...` from repo root."""
    args = sys.argv[1:]
    if args and args[0] == "app.main:app":
        _run_backend(["uvicorn", *args])
    print(
        "Root uvicorn is reserved for the backend app. "
        "Use `cd backend && poetry run uvicorn app.main:app --reload`, "
        "or from root: `poetry run uvicorn app.main:app --reload`."
    )
    raise SystemExit(2)
