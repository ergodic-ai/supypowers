# /// script
# dependencies = [
#   "pydantic",
# ]
# ///
"""
files.py - File operations for agents

Run with:
  supypowers run files:read '{"path": "README.md"}'
  supypowers run files:write '{"path": "output.txt", "content": "Hello!"}'
  supypowers run files:list_dir '{"path": "."}'
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class ReadInput(BaseModel):
    path: str = Field(..., description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")


class ReadOutput(BaseModel):
    success: bool
    content: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None


def read(input: ReadInput) -> ReadOutput:
    """Read a file and return its contents."""
    try:
        p = Path(input.path).resolve()
        if not p.exists():
            return ReadOutput(success=False, error=f"File not found: {input.path}")
        if not p.is_file():
            return ReadOutput(success=False, error=f"Not a file: {input.path}")
        
        content = p.read_text(encoding=input.encoding)
        return ReadOutput(
            success=True,
            content=content[:100000],  # Limit size
            size_bytes=p.stat().st_size,
        )
    except Exception as e:
        return ReadOutput(success=False, error=str(e))


class WriteInput(BaseModel):
    path: str = Field(..., description="Path to write to")
    content: str = Field(..., description="Content to write")
    encoding: str = Field(default="utf-8", description="File encoding")
    append: bool = Field(default=False, description="Append instead of overwrite")


class WriteOutput(BaseModel):
    success: bool
    path: Optional[str] = None
    bytes_written: Optional[int] = None
    error: Optional[str] = None


def write(input: WriteInput) -> WriteOutput:
    """Write content to a file."""
    try:
        p = Path(input.path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if input.append else "w"
        with open(p, mode, encoding=input.encoding) as f:
            f.write(input.content)
        
        return WriteOutput(
            success=True,
            path=str(p),
            bytes_written=len(input.content.encode(input.encoding)),
        )
    except Exception as e:
        return WriteOutput(success=False, error=str(e))


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Directory path to list")
    pattern: str = Field(default="*", description="Glob pattern to filter")
    recursive: bool = Field(default=False, description="List recursively")


class FileInfo(BaseModel):
    name: str
    path: str
    is_dir: bool
    size_bytes: Optional[int] = None


class ListDirOutput(BaseModel):
    success: bool
    files: Optional[list[FileInfo]] = None
    error: Optional[str] = None


def list_dir(input: ListDirInput) -> ListDirOutput:
    """List files in a directory."""
    try:
        p = Path(input.path).resolve()
        if not p.exists():
            return ListDirOutput(success=False, error=f"Path not found: {input.path}")
        if not p.is_dir():
            return ListDirOutput(success=False, error=f"Not a directory: {input.path}")
        
        glob_func = p.rglob if input.recursive else p.glob
        files = []
        for item in sorted(glob_func(input.pattern))[:1000]:  # Limit results
            files.append(FileInfo(
                name=item.name,
                path=str(item),
                is_dir=item.is_dir(),
                size_bytes=item.stat().st_size if item.is_file() else None,
            ))
        
        return ListDirOutput(success=True, files=files)
    except Exception as e:
        return ListDirOutput(success=False, error=str(e))
