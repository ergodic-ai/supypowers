# /// script
# dependencies = [
#   "pydantic",
# ]
# ///

from __future__ import annotations

from pydantic import BaseModel, Field


class ReverseStringInput(BaseModel):
    s: str = Field(..., description="String to reverse.")


class ReverseStringOutput(BaseModel):
    result: str = Field(..., description="The reversed string.")


def reverse_string(input: ReverseStringInput) -> ReverseStringOutput:
    """Reverse a string."""
    return ReverseStringOutput(result=input.s[::-1])


class CountVowelsInput(BaseModel):
    s: str = Field(..., description="String to count vowels in.")


class CountVowelsOutput(BaseModel):
    count: int = Field(..., description="Number of vowels in the string.")


def count_vowels(input: CountVowelsInput) -> CountVowelsOutput:
    """Count vowels in a string."""
    vowels = set("aeiouAEIOU")
    return CountVowelsOutput(count=sum(1 for ch in input.s if ch in vowels))

