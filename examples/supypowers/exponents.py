# /// script
# dependencies = [
#   "pydantic",
# ]
# ///

import sys
from math import sqrt
from pydantic import BaseModel, Field


class ComputeSqrtInput(BaseModel):
    x: float = Field(..., description="The number to compute the square root of.")


class ComputeSqrtOutput(BaseModel):
    result: float = Field(..., description="The square root of the number.")


def compute_sqrt(input: ComputeSqrtInput) -> ComputeSqrtOutput:
    """This function computes the square root of a number."""
    return ComputeSqrtOutput(result=sqrt(input.x))


class ComputeDifferentPowerInput(BaseModel):
    x: float = Field(..., description="The number to compute the different powers of.")
    n: int = Field(..., description="The power to compute.")


class ComputeDifferentPowerOutput(BaseModel):
    result: float = Field(..., description="The different powers of the number.")


def compute_different_power(
    input: ComputeDifferentPowerInput,
) -> ComputeDifferentPowerOutput:
    """This function computes the different powers of a number."""
    return ComputeDifferentPowerOutput(result=input.x**input.n)


if __name__ == "__main__":
    print(sys.argv)
