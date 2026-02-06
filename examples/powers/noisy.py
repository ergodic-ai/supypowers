# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
noisy.py - Test script that prints to stdout before returning.

Used to verify that stdout isolation prevents stray output from
corrupting the runner's JSON result.
"""
from pydantic import BaseModel, Field


class NoisyInput(BaseModel):
    message: str = Field(..., description="Message to echo back.")


class NoisyOutput(BaseModel):
    echoed: str = Field(..., description="The echoed message.")


def noisy(input: NoisyInput) -> NoisyOutput:
    """Echo back the message, but also print noise to stdout."""
    print("NOISE_BEFORE")
    print("MORE NOISE")
    return NoisyOutput(echoed=input.message)
