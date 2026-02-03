# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
hello.py - Example supypower script

Run with:   supypowers run hello:hello "{'name': 'World'}"
"""
from pydantic import BaseModel, Field


# ============================================================================
# STEP 1: Define your INPUT model (required)
# ============================================================================
class HelloInput(BaseModel):
    name: str = Field(..., description="Name to greet.")


# ============================================================================
# STEP 2: Define your OUTPUT model (recommended but optional)
# ============================================================================
class HelloOutput(BaseModel):
    greeting: str = Field(..., description="A friendly greeting.")


# ============================================================================
# STEP 3: Write your function
# - Must have exactly ONE parameter named `input`
# - `input` must be typed as a Pydantic BaseModel
# - Add a docstring (it becomes the function's description)
# ============================================================================
def hello(input: HelloInput) -> HelloOutput:
    """Generate a friendly greeting for the given name."""
    return HelloOutput(greeting=f"Hello, {input.name}!")
