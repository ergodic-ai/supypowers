from __future__ import annotations

import ast
from pathlib import Path
from typing import List


def read_uv_script_dependencies(script_path: Path) -> List[str]:
    """
    Parse `uv` inline script metadata and return its dependency strings.

    Supports the common form:

    # /// script
    # dependencies = [
    #   "pydantic",
    # ]
    # ///
    """
    try:
        text = script_path.read_text(encoding="utf-8")
    except Exception:
        return []

    lines = text.splitlines()
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip() == "# /// script":
            start = i + 1
            continue
        if start is not None and line.strip() == "# ///":
            end = i
            break

    if start is None or end is None or end <= start:
        return []

    # Strip leading comment markers.
    meta_lines = []
    for raw in lines[start:end]:
        s = raw.lstrip()
        if s.startswith("#"):
            s = s[1:]
            if s.startswith(" "):
                s = s[1:]
        meta_lines.append(s)

    meta_src = "\n".join(meta_lines).strip()
    if not meta_src:
        return []

    # Parse assignments in the metadata block.
    try:
        tree = ast.parse(meta_src, mode="exec")
    except Exception:
        return []

    deps: List[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "dependencies":
            continue
        try:
            value = ast.literal_eval(node.value)
        except Exception:
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    deps.append(item)
        break

    return deps

