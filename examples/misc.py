# /// script
# dependencies = [
#   "pydantic",
# ]
# ///

from __future__ import annotations

from pydantic import BaseModel, Field


class EchoInput(BaseModel):
    message: str = Field(..., description="Message to echo back.")


def echo(input: EchoInput) -> str:
    """Return a plain string (non-Pydantic output)."""
    return input.message

