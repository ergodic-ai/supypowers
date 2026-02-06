# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
text.py - Text processing utilities

Run with:
  supypowers run text:regex_search '{"text": "hello world", "pattern": "\\\\w+"}'
  supypowers run text:replace '{"text": "hello world", "find": "world", "replace": "agent"}'
  supypowers run text:extract_json '{"text": "prefix {\"key\": \"value\"} suffix"}'
"""
import re
import json
from typing import Optional
from pydantic import BaseModel, Field


class RegexSearchInput(BaseModel):
    text: str = Field(..., description="Text to search in")
    pattern: str = Field(..., description="Regex pattern")
    flags: str = Field(default="", description="Regex flags: i=ignorecase, m=multiline, s=dotall")


class RegexMatch(BaseModel):
    match: str
    start: int
    end: int
    groups: list[str]


class RegexSearchOutput(BaseModel):
    success: bool
    matches: Optional[list[RegexMatch]] = None
    count: Optional[int] = None
    error: Optional[str] = None


def regex_search(input: RegexSearchInput) -> RegexSearchOutput:
    """Search text using a regular expression."""
    try:
        flags = 0
        if "i" in input.flags:
            flags |= re.IGNORECASE
        if "m" in input.flags:
            flags |= re.MULTILINE
        if "s" in input.flags:
            flags |= re.DOTALL
        
        matches = []
        for m in re.finditer(input.pattern, input.text, flags):
            matches.append(RegexMatch(
                match=m.group(0),
                start=m.start(),
                end=m.end(),
                groups=list(m.groups()),
            ))
            if len(matches) >= 100:  # Limit results
                break
        
        return RegexSearchOutput(success=True, matches=matches, count=len(matches))
    except Exception as e:
        return RegexSearchOutput(success=False, error=str(e))


class ReplaceInput(BaseModel):
    text: str = Field(..., description="Text to modify")
    find: str = Field(..., description="String or regex to find")
    replace: str = Field(..., description="Replacement string")
    regex: bool = Field(default=False, description="Treat 'find' as a regex pattern")
    count: int = Field(default=0, description="Max replacements (0 = unlimited)")


class ReplaceOutput(BaseModel):
    success: bool
    result: Optional[str] = None
    replacements_made: Optional[int] = None
    error: Optional[str] = None


def replace(input: ReplaceInput) -> ReplaceOutput:
    """Find and replace in text."""
    try:
        if input.regex:
            result, n = re.subn(input.find, input.replace, input.text, count=input.count or 0)
        else:
            if input.count:
                result = input.text.replace(input.find, input.replace, input.count)
                n = min(input.text.count(input.find), input.count)
            else:
                n = input.text.count(input.find)
                result = input.text.replace(input.find, input.replace)
        
        return ReplaceOutput(success=True, result=result, replacements_made=n)
    except Exception as e:
        return ReplaceOutput(success=False, error=str(e))


class ExtractJsonInput(BaseModel):
    text: str = Field(..., description="Text containing JSON")


class ExtractJsonOutput(BaseModel):
    success: bool
    objects: Optional[list] = None
    error: Optional[str] = None


def extract_json(input: ExtractJsonInput) -> ExtractJsonOutput:
    """Extract JSON objects from text (finds all {...} and [...] patterns)."""
    try:
        objects = []
        
        # Find JSON objects and arrays
        for pattern in [r'\{[^{}]*\}', r'\[[^\[\]]*\]']:
            for match in re.finditer(pattern, input.text):
                try:
                    obj = json.loads(match.group())
                    objects.append(obj)
                except json.JSONDecodeError:
                    pass
        
        # Also try nested JSON (simple approach)
        depth = 0
        start = None
        for i, c in enumerate(input.text):
            if c in '{[':
                if depth == 0:
                    start = i
                depth += 1
            elif c in '}]':
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        obj = json.loads(input.text[start:i+1])
                        if obj not in objects:
                            objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start = None
        
        return ExtractJsonOutput(success=True, objects=objects[:20])  # Limit results
    except Exception as e:
        return ExtractJsonOutput(success=False, error=str(e))
