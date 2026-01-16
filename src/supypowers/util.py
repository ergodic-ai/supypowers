from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable


def resolve_script_path(folder: Path, script_name: str) -> Path:
    """
    Resolve a script name (with or without .py) within a folder.
    """
    name = script_name if script_name.endswith(".py") else f"{script_name}.py"
    p = (folder / name).resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Script not found: {p}")
    return p


def _parse_dotenv(text: str) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            env[k] = v
    return env


def parse_secrets_args(secrets_args: Iterable[str]) -> Dict[str, str]:
    """
    Accept secrets as either:
    - a path to a dotenv file
    - inline KEY=VAL
    """
    out: Dict[str, str] = {}
    for s in secrets_args:
        if "=" in s and not Path(s).exists():
            k, v = s.split("=", 1)
            out[k] = v
            continue
        p = Path(s)
        if p.exists() and p.is_file():
            out.update(_parse_dotenv(p.read_text(encoding="utf-8")))
            continue
        # Fall back: if it contains '=', treat as inline even if the path doesn't exist.
        if "=" in s:
            k, v = s.split("=", 1)
            out[k] = v
            continue
        raise ValueError(f"--secrets value must be a .env path or KEY=VAL, got: {s}")
    return out

