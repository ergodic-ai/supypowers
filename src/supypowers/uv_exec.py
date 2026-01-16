from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from supypowers.uv_script_metadata import read_uv_script_dependencies


@dataclass(frozen=True)
class UVRunError(Exception):
    message: str
    exit_code: int
    stdout: str
    stderr: str


def uv_run_python_code(
    *,
    script_path: Path,
    code: str,
    payload: dict,
    extra_env: Optional[Dict[str, str]] = None,
    quiet: bool = True,
) -> str:
    """
    Execute `python -c <code>` in a uv environment built from `script_path` inline dependencies,
    sending `payload` via stdin and returning stdout.
    """
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    deps = read_uv_script_dependencies(script_path)

    cmd = ["uv", "run", "--no-project"]
    if quiet:
        cmd.extend(["-q", "--no-progress"])
    for dep in deps:
        cmd.extend(["--with", dep])
    cmd.extend(["python", "-c", code])

    proc = subprocess.run(
        cmd,
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    stdout = proc.stdout.decode("utf-8", errors="replace").strip()
    stderr = proc.stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        raise UVRunError(
            message=f"`uv run` failed with exit code {proc.returncode}",
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return stdout

