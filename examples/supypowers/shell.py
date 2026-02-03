# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
shell.py - Run shell commands

Run with:
  supypowers run shell:run '{"command": "echo hello"}'
  supypowers run shell:run '{"command": "ls -la", "cwd": "/tmp"}'
"""
import subprocess
import shlex
from typing import Optional
from pydantic import BaseModel, Field


class RunInput(BaseModel):
    command: str = Field(..., description="Shell command to run")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    timeout: int = Field(default=60, description="Timeout in seconds")
    shell: bool = Field(default=True, description="Run through shell (allows pipes, etc)")


class RunOutput(BaseModel):
    success: bool
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None


def run(input: RunInput) -> RunOutput:
    """Execute a shell command and return its output."""
    try:
        if input.shell:
            cmd = input.command
        else:
            cmd = shlex.split(input.command)
        
        result = subprocess.run(
            cmd,
            shell=input.shell,
            cwd=input.cwd,
            capture_output=True,
            text=True,
            timeout=input.timeout,
        )
        
        return RunOutput(
            success=result.returncode == 0,
            exit_code=result.returncode,
            stdout=result.stdout[:50000] if result.stdout else None,
            stderr=result.stderr[:50000] if result.stderr else None,
        )
    except subprocess.TimeoutExpired:
        return RunOutput(success=False, error=f"Command timed out after {input.timeout}s")
    except Exception as e:
        return RunOutput(success=False, error=str(e))
