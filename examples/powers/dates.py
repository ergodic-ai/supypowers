# /// script
# dependencies = [
#   "pydantic",
# ]
# ///

from datetime import date, timedelta

from pydantic import BaseModel, Field


class AddDaysInput(BaseModel):
    d: date = Field(..., description="Date (YYYY-MM-DD).")
    days: int = Field(..., description="Days to add (can be negative).")


class AddDaysOutput(BaseModel):
    result: date = Field(..., description="Resulting date (YYYY-MM-DD).")


def add_days(input: AddDaysInput) -> AddDaysOutput:
    """Add (or subtract) a number of days from a date."""
    return AddDaysOutput(result=input.d + timedelta(days=input.days))


class DaysBetweenInput(BaseModel):
    start: date = Field(..., description="Start date (YYYY-MM-DD).")
    end: date = Field(..., description="End date (YYYY-MM-DD).")


class DaysBetweenOutput(BaseModel):
    days: int = Field(..., description="Number of days between end and start.")


def days_between(input: DaysBetweenInput) -> DaysBetweenOutput:
    """Compute the day delta between two dates (end - start)."""
    return DaysBetweenOutput(days=(input.end - input.start).days)

