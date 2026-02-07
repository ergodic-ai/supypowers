from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_uv_superpowers(*args: str, cwd: str | None = None) -> dict:
    """
    Run: uv run supypowers <args...>
    and parse stdout as JSON.
    """
    if shutil.which("uv") is None:
        raise unittest.SkipTest("uv not found on PATH")

    cmd = ["uv", "run", "supypowers", *args]
    proc = subprocess.run(
        cmd,
        cwd=cwd or str(ROOT),
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


def _run_uv_superpowers_raw(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run supypowers and return the raw CompletedProcess (no assertion on returncode)."""
    if shutil.which("uv") is None:
        raise unittest.SkipTest("uv not found on PATH")

    cmd = ["uv", "run", "supypowers", *args]
    return subprocess.run(
        cmd,
        cwd=cwd or str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
        text=True,
    )


class TestCLI(unittest.TestCase):
    def test_init_creates_templates(self) -> None:
        tmp = ROOT / "tests" / ".tmp_init"
        if tmp.exists():
            # best-effort cleanup
            for p in sorted(tmp.rglob("*"), reverse=True):
                if p.is_file() or p.is_symlink():
                    p.unlink()
                elif p.is_dir():
                    p.rmdir()
            tmp.rmdir()
        tmp.mkdir(parents=True, exist_ok=False)

        # init should create <tmp>/powers/hello.py and hello.md
        out = _run_uv_superpowers("init", "--root", str(tmp), "--force")
        self.assertTrue(out["ok"])
        sp_dir = tmp / "powers"
        self.assertTrue((sp_dir / "hello.py").exists())
        self.assertTrue((sp_dir / "hello.md").exists())

    def test_docs_includes_exponents(self) -> None:
        docs = _run_uv_superpowers("docs", "--examples")
        # docs is a list of {"script": ..., "functions": [...]}
        by_script = {Path(item["script"]).name: item for item in docs}
        self.assertIn("exponents.py", by_script)
        fn_names = {f["name"] for f in by_script["exponents.py"]["functions"]}
        self.assertIn("compute_sqrt", fn_names)
        self.assertIn("compute_different_power", fn_names)

    def test_docs_markdown_renders(self) -> None:
        # Just ensure it runs and produces markdown-like output.
        cmd = ["uv", "run", "supypowers", "docs", "--examples", "--format", "md"]
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr}\nstdout={proc.stdout}")
        # SKILL.md format: YAML frontmatter + heading + function sections
        self.assertIn("---", proc.stdout)
        self.assertIn("name: supypowers-reference", proc.stdout)
        self.assertIn("# Supypowers", proc.stdout)
        self.assertIn("## `", proc.stdout)

    def test_run_exponents_compute_sqrt(self) -> None:
        out = _run_uv_superpowers("run", "--examples", "exponents:compute_sqrt", "{'x': 9}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], 3.0)

    def test_run_strings_reverse(self) -> None:
        out = _run_uv_superpowers("run", "--examples", "strings:reverse_string", "{'s': 'abc'}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], "cba")

    def test_run_dates_add_days(self) -> None:
        out = _run_uv_superpowers(
            "run",
            "--examples",
            "dates:add_days",
            "{'d': '2025-01-01', 'days': 10}",
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result"], "2025-01-11")

    def test_run_noisy_stdout_isolated(self) -> None:
        out = _run_uv_superpowers("run", "--examples", "noisy:noisy", "{'message': 'hello'}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["echoed"], "hello")

    def test_run_non_pydantic_output_allowed(self) -> None:
        out = _run_uv_superpowers("run", "--examples", "misc:echo", "{'message': 'hi'}")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"], "hi")

    def test_test_auto_generates_input(self) -> None:
        proc = _run_uv_superpowers_raw(
            "test", "--examples", "exponents:compute_sqrt"
        )
        self.assertEqual(proc.returncode, 0)
        last_line = proc.stdout.strip().splitlines()[-1]
        out = json.loads(last_line)
        self.assertTrue(out["ok"])

    def test_test_with_fixture(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"x": 25}')
            f.flush()
            try:
                proc = _run_uv_superpowers_raw(
                    "test", "--examples", "exponents:compute_sqrt", "--fixture", f.name
                )
                self.assertEqual(proc.returncode, 0)
                last_line = proc.stdout.strip().splitlines()[-1]
                out = json.loads(last_line)
                self.assertTrue(out["ok"])
                self.assertEqual(out["data"]["result"], 5.0)
            finally:
                os.unlink(f.name)


class TestCLIErrors(unittest.TestCase):
    """Tests for error paths in CLI commands."""

    def test_run_bad_target_no_colon(self) -> None:
        proc = _run_uv_superpowers_raw("run", "--examples", "exponents", "{}")
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["ok"])
        self.assertIn("script:function", out["error"])

    def test_run_nonexistent_script(self) -> None:
        proc = _run_uv_superpowers_raw("run", "--examples", "nonexistent:func", "{}")
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["ok"])
        self.assertIn("Script not found", out["error"])

    def test_test_nonexistent_script_returns_json(self) -> None:
        """'test' with nonexistent script should return JSON, not a traceback."""
        proc = _run_uv_superpowers_raw("test", "--examples", "nonexistent:func")
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["ok"])
        self.assertIn("Script not found", out["error"])

    def test_run_nonexistent_function(self) -> None:
        proc = _run_uv_superpowers_raw(
            "run", "--examples", "exponents:no_such_func", "{}"
        )
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["ok"])
        # The error comes through either as a direct message or via uv_stdout
        error_text = out.get("error", "") + out.get("uv_stdout", "")
        self.assertIn("function not found", error_text)

    def test_run_pydantic_validation_error(self) -> None:
        # compute_sqrt requires 'x' (float), pass wrong field name
        proc = _run_uv_superpowers_raw(
            "run", "--examples", "exponents:compute_sqrt", '{"wrong_field": 1}'
        )
        self.assertNotEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["ok"])

    def test_run_invalid_json_input(self) -> None:
        proc = _run_uv_superpowers_raw(
            "run", "--examples", "exponents:compute_sqrt", "not json at all %%"
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_init_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # First init
            _run_uv_superpowers("init", "--root", tmp, "--force")
            # Second init without --force should fail
            proc = _run_uv_superpowers_raw("init", "--root", tmp)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertFalse(out["ok"])
            self.assertIn("refusing to overwrite", out["error"])


class TestNew(unittest.TestCase):
    """Tests for the 'new' command."""

    def test_new_creates_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # First init to create powers/
            _run_uv_superpowers("init", "--root", tmp, "--force")
            # Create a new script
            out = _run_uv_superpowers("new", "my_tool", "--root", tmp)
            self.assertTrue(out["ok"])
            script = Path(tmp) / "powers" / "my_tool.py"
            self.assertTrue(script.exists())
            content = script.read_text()
            self.assertIn("class MyToolInput", content)
            self.assertIn("class MyToolOutput", content)
            self.assertIn("def my_tool(input:", content)

    def test_new_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _run_uv_superpowers("init", "--root", tmp, "--force")
            _run_uv_superpowers("new", "my_tool", "--root", tmp)
            # Second new without --force should fail
            proc = _run_uv_superpowers_raw("new", "my_tool", "--root", tmp)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertFalse(out["ok"])
            self.assertIn("already exists", out["error"])

    def test_new_invalid_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _run_uv_superpowers("init", "--root", tmp, "--force")
            proc = _run_uv_superpowers_raw("new", "123-bad!", "--root", tmp)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertFalse(out["ok"])
            self.assertIn("invalid script name", out["error"])

    def test_new_no_powers_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run_uv_superpowers_raw("new", "my_tool", "--root", tmp)
            self.assertNotEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertFalse(out["ok"])
            self.assertIn("folder not found", out["error"])


class TestSkills(unittest.TestCase):
    """Tests for the 'skills' command."""

    def test_skills_examples(self) -> None:
        # skills doesn't support --examples, so test with an init'd folder
        with tempfile.TemporaryDirectory() as tmp:
            _run_uv_superpowers("init", "--root", tmp, "--force")
            proc = _run_uv_superpowers_raw("skills", "--root", tmp)
            self.assertEqual(proc.returncode, 0)
            out = proc.stdout
            self.assertIn("---", out)
            self.assertIn("name: supypowers", out)
            self.assertIn("# Supypowers", out)

    def test_skills_output_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _run_uv_superpowers("init", "--root", tmp, "--force")
            outfile = Path(tmp) / "SKILL.md"
            out = _run_uv_superpowers("skills", "--root", tmp, "--output", str(outfile))
            self.assertTrue(out["ok"])
            self.assertTrue(outfile.exists())
            content = outfile.read_text()
            self.assertIn("name: supypowers", content)


class TestLegacyFolderFallback(unittest.TestCase):
    """Tests for backward-compat supypowers/ -> powers/ fallback."""

    _LEGACY_SCRIPT = (
        '# /// script\n# dependencies = ["pydantic"]\n# ///\n'
        'from pydantic import BaseModel, Field\n'
        'class HiInput(BaseModel):\n'
        '    name: str = Field(...)\n'
        'class HiOutput(BaseModel):\n'
        '    greeting: str = Field(...)\n'
        'def hello(input: HiInput) -> HiOutput:\n'
        '    """Say hi."""\n'
        '    return HiOutput(greeting=f"Hi {input.name}")\n'
    )

    def _make_legacy_dir(self, tmp: str) -> Path:
        legacy_dir = Path(tmp) / "supypowers"
        legacy_dir.mkdir()
        (legacy_dir / "hello.py").write_text(self._LEGACY_SCRIPT)
        return legacy_dir

    def test_legacy_folder_fallback_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._make_legacy_dir(tmp)
            # Run against the legacy folder — should work with deprecation warning
            proc = _run_uv_superpowers_raw(
                "run", "--root", tmp, "hello:hello", '{"name": "World"}'
            )
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertTrue(out["ok"])
            self.assertEqual(out["data"]["greeting"], "Hi World")
            self.assertIn("deprecated", proc.stderr)

    def test_legacy_folder_new_command(self) -> None:
        """'new' should work when only supypowers/ exists (legacy fallback)."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_legacy_dir(tmp)
            proc = _run_uv_superpowers_raw("new", "my_tool", "--root", tmp)
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertTrue(out["ok"])
            self.assertTrue((Path(tmp) / "supypowers" / "my_tool.py").exists())
            self.assertIn("deprecated", proc.stderr)

    def test_legacy_folder_docs_command(self) -> None:
        """'docs' should work when only supypowers/ exists (legacy fallback)."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_legacy_dir(tmp)
            proc = _run_uv_superpowers_raw("docs", "--root", tmp, "--format", "json")
            self.assertEqual(proc.returncode, 0)
            docs = json.loads(proc.stdout.strip())
            self.assertIsInstance(docs, list)
            self.assertTrue(len(docs) > 0)
            fn_names = {fn["name"] for fn in docs[0].get("functions", [])}
            self.assertIn("hello", fn_names)
            self.assertIn("deprecated", proc.stderr)

    def test_legacy_folder_test_command(self) -> None:
        """'test' should work when only supypowers/ exists (legacy fallback)."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_legacy_dir(tmp)
            proc = _run_uv_superpowers_raw(
                "test", "--root", tmp, "hello:hello"
            )
            self.assertEqual(proc.returncode, 0)
            # stdout has the JSON result on the last line
            last_line = proc.stdout.strip().splitlines()[-1]
            out = json.loads(last_line)
            self.assertTrue(out["ok"])
            self.assertIn("deprecated", proc.stderr)

    def test_legacy_folder_skills_command(self) -> None:
        """'skills' should work when only supypowers/ exists (legacy fallback)."""
        with tempfile.TemporaryDirectory() as tmp:
            self._make_legacy_dir(tmp)
            proc = _run_uv_superpowers_raw("skills", "--root", tmp)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("name: supypowers", proc.stdout)
            self.assertIn("hello:hello", proc.stdout)
            self.assertIn("deprecated", proc.stderr)

    def test_powers_folder_preferred_over_legacy(self) -> None:
        """When both powers/ and supypowers/ exist, powers/ takes precedence."""
        with tempfile.TemporaryDirectory() as tmp:
            # Create both folders with different scripts
            self._make_legacy_dir(tmp)
            powers_dir = Path(tmp) / "powers"
            powers_dir.mkdir()
            (powers_dir / "hello.py").write_text(
                '# /// script\n# dependencies = ["pydantic"]\n# ///\n'
                'from pydantic import BaseModel, Field\n'
                'class HiInput(BaseModel):\n'
                '    name: str = Field(...)\n'
                'class HiOutput(BaseModel):\n'
                '    greeting: str = Field(...)\n'
                'def hello(input: HiInput) -> HiOutput:\n'
                '    """Say hi."""\n'
                '    return HiOutput(greeting=f"MODERN {input.name}")\n'
            )
            proc = _run_uv_superpowers_raw(
                "run", "--root", tmp, "hello:hello", '{"name": "World"}'
            )
            self.assertEqual(proc.returncode, 0)
            out = json.loads(proc.stdout.strip())
            self.assertTrue(out["ok"])
            # Should use powers/ (modern), not supypowers/ (legacy)
            self.assertEqual(out["data"]["greeting"], "MODERN World")
            # No deprecation warning since powers/ was found
            self.assertNotIn("deprecated", proc.stderr)


class TestUtilUnit(unittest.TestCase):
    """Unit tests for util.py helpers (no uv needed)."""

    def test_parse_dotenv(self) -> None:
        from supypowers.util import _parse_dotenv

        text = """
# comment
FOO=bar
BAZ="quoted value"
export EXPORTED=yes
EMPTY=

invalid line without equals
"""
        result = _parse_dotenv(text)
        self.assertEqual(result["FOO"], "bar")
        self.assertEqual(result["BAZ"], "quoted value")
        self.assertEqual(result["EXPORTED"], "yes")
        self.assertEqual(result["EMPTY"], "")

    def test_parse_secrets_args_inline(self) -> None:
        from supypowers.util import parse_secrets_args

        result = parse_secrets_args(["KEY1=val1", "KEY2=val2"])
        self.assertEqual(result, {"KEY1": "val1", "KEY2": "val2"})

    def test_parse_secrets_args_dotenv_file(self) -> None:
        from supypowers.util import parse_secrets_args

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SECRET=from_file\n")
            f.flush()
            try:
                result = parse_secrets_args([f.name])
                self.assertEqual(result["SECRET"], "from_file")
            finally:
                os.unlink(f.name)

    def test_parse_secrets_args_invalid(self) -> None:
        from supypowers.util import parse_secrets_args

        with self.assertRaises(ValueError):
            parse_secrets_args(["not_a_file_and_no_equals"])

    def test_resolve_script_path(self) -> None:
        from supypowers.util import resolve_script_path

        examples = ROOT / "examples" / "powers"
        # With .py suffix
        p = resolve_script_path(examples, "exponents.py")
        self.assertTrue(p.exists())
        # Without .py suffix
        p = resolve_script_path(examples, "exponents")
        self.assertTrue(p.exists())

    def test_resolve_script_path_not_found(self) -> None:
        from supypowers.util import resolve_script_path

        examples = ROOT / "examples" / "powers"
        with self.assertRaises(FileNotFoundError):
            resolve_script_path(examples, "does_not_exist")


class TestScriptMetadataUnit(unittest.TestCase):
    """Unit tests for uv_script_metadata.py (no uv needed)."""

    def test_read_dependencies(self) -> None:
        from supypowers.uv_script_metadata import read_uv_script_dependencies

        script = ROOT / "examples" / "powers" / "exponents.py"
        deps = read_uv_script_dependencies(script)
        self.assertIn("pydantic", deps)

    def test_read_dependencies_multi(self) -> None:
        from supypowers.uv_script_metadata import read_uv_script_dependencies

        script = ROOT / "examples" / "powers" / "fetch.py"
        deps = read_uv_script_dependencies(script)
        self.assertIn("pydantic", deps)
        self.assertIn("httpx", deps)

    def test_read_dependencies_no_block(self) -> None:
        from supypowers.uv_script_metadata import read_uv_script_dependencies

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# no script block here\nprint('hello')\n")
            f.flush()
            try:
                deps = read_uv_script_dependencies(Path(f.name))
                self.assertEqual(deps, [])
            finally:
                os.unlink(f.name)

    def test_read_dependencies_nonexistent_file(self) -> None:
        from supypowers.uv_script_metadata import read_uv_script_dependencies

        deps = read_uv_script_dependencies(Path("/nonexistent/path.py"))
        self.assertEqual(deps, [])


class TestToClassName(unittest.TestCase):
    """Unit tests for _to_class_name helper."""

    def test_snake_to_pascal(self) -> None:
        from supypowers.cli import _to_class_name

        self.assertEqual(_to_class_name("my_tool"), "MyTool")
        self.assertEqual(_to_class_name("fetch_weather"), "FetchWeather")
        self.assertEqual(_to_class_name("simple"), "Simple")
        self.assertEqual(_to_class_name("a_b_c"), "ABC")


if __name__ == "__main__":
    unittest.main()

