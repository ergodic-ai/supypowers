from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _run_uv_superpowers(*args: str) -> dict:
    """
    Run: uv run supypowers <args...>
    and parse stdout as JSON.
    """
    if shutil.which("uv") is None:
        raise unittest.SkipTest("uv not found on PATH")

    cmd = ["uv", "run", "supypowers", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
        text=True,
    )
    out = proc.stdout.strip()
    err = proc.stderr.strip()
    if proc.returncode != 0:
        raise AssertionError(f"command failed ({proc.returncode})\ncmd={cmd}\nstdout={out}\nstderr={err}")
    try:
        return json.loads(out)
    except Exception as e:
        raise AssertionError(f"stdout was not JSON\ncmd={cmd}\nstdout={out}\nstderr={err}\nerr={e}")


class TestCLI(unittest.TestCase):
    def test_docs_includes_exponents(self) -> None:
        docs = _run_uv_superpowers(str(EXAMPLES), "docs")
        # docs is a list of {"script": ..., "functions": [...]}
        by_script = {Path(item["script"]).name: item for item in docs}
        self.assertIn("exponents.py", by_script)
        fn_names = {f["name"] for f in by_script["exponents.py"]["functions"]}
        self.assertIn("compute_sqrt", fn_names)
        self.assertIn("compute_different_power", fn_names)

    def test_docs_markdown_renders(self) -> None:
        # Just ensure it runs and produces markdown-like output.
        cmd = ["uv", "run", "supypowers", str(EXAMPLES), "docs", "--format", "md"]
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr}\nstdout={proc.stdout}")
        self.assertIn("## Supypowers", proc.stdout)
        self.assertIn("### `", proc.stdout)

    def test_run_exponents_compute_sqrt(self) -> None:
        out = _run_uv_superpowers(str(EXAMPLES), "run", "exponents:compute_sqrt", "{'x': 9}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], 3.0)

    def test_run_strings_reverse(self) -> None:
        out = _run_uv_superpowers(str(EXAMPLES), "run", "strings:reverse_string", "{'s': 'abc'}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], "cba")

    def test_run_dates_add_days(self) -> None:
        out = _run_uv_superpowers(
            str(EXAMPLES),
            "run",
            "dates:add_days",
            "{'d': '2025-01-01', 'days': 10}",
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], "2025-01-11")

    def test_run_non_pydantic_output_allowed(self) -> None:
        out = _run_uv_superpowers(str(EXAMPLES), "run", "misc:echo", "{'message': 'hi'}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"], "hi")


if __name__ == "__main__":
    unittest.main()

