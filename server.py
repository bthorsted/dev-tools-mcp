"""Dev Tools MCP Server.

Exposes common Python development tools (pytest, ruff, pyright) as MCP tools
using the high-level FastMCP API.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dev-tools")


def _run(command: list[str]) -> str:
    """Run a command as a subprocess and return a structured result string.

    Captures both stdout and stderr and reports the process exit code. If the
    executable cannot be found, a helpful error message is returned instead of
    raising, so the MCP client always receives a usable response.
    """
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return (
            f"Exit code: 127\n"
            f"stdout:\n\n"
            f"stderr:\nCommand not found: {command[0]!r}. "
            f"Make sure it is installed and available on PATH."
        )

    return (
        f"Exit code: {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


@mcp.tool()
def run_pytest(args: list[str] | None = None) -> str:
    """Run `pytest` with optional arguments.

    The `--json-report` flag is prepended (via the `pytest-json-report`
    plugin) so pytest produces a structured JSON report. The report is written
    to a temporary file, read back, and appended to the response under a
    "JSON report:" section. The report includes a `tests` array with each
    test's outcome, duration, and failure details — exactly what an agent
    needs to ingest results programmatically.

    Args:
        args: A list of string arguments passed directly to pytest, e.g.
            ["src/", "-k", "test_login", "-m", "not slow"]. Pass an empty
            list or omit to run pytest with just the JSON report defaults.

    Returns:
        A structured string containing the exit code, stdout, and stderr,
        followed by the full JSON report.
    """
    fd, report_path = tempfile.mkstemp(prefix="pytest-report-", suffix=".json")
    os.close(fd)
    try:
        result = _run(
            [
                "uv", "run",
                "pytest",
                "--json-report",
                f"--json-report-file={report_path}",
                *(args or []),
            ]
        )
        try:
            with open(report_path, encoding="utf-8") as fh:
                report = fh.read()
        except OSError:
            report = ""
    finally:
        try:
            os.remove(report_path)
        except OSError:
            pass

    if report:
        return f"{result}\nJSON report:\n{report}"
    return result


@mcp.tool()
def run_ruff_check(args: list[str] | None = None) -> str:
    """Run `ruff check` with optional arguments.

    By default `--output-format json` is prepended so ruff emits a JSON array
    of diagnostic objects (instead of the human-readable "full" format with
    code excerpts), which is easier for an agent to parse. Supplying your own
    `--output-format` overrides this default.

    Args:
        args: A list of string arguments passed directly to `ruff check`, e.g.
            ["src/", "--fix", "--select", "E,F"]. Pass an empty list or omit
            to check the current directory.

    Returns:
        A structured string containing the exit code, stdout, and stderr.
    """
    return _run(["uv", "run", "ruff", "check", "--output-format", "json", *(args or [])])


@mcp.tool()
def run_ruff_format(args: list[str] | None = None) -> str:
    """Run `ruff format` with optional arguments.

    Args:
        args: A list of string arguments passed directly to `ruff format`, e.g.
            ["src/", "--check"]. Pass an empty list or omit to format the
            current directory.

    Returns:
        A structured string containing the exit code, stdout, and stderr.
    """
    return _run(["uv", "run", "ruff", "format", *(args or [])])


@mcp.tool()
def run_pyright(args: list[str] | None = None) -> str:
    """Run `pyright` with optional arguments.

    By default `--outputjson` is prepended so pyright emits a structured JSON
    object with a `generalDiagnostics` array, which is easier for an agent to
    parse than the default text output.

    Args:
        args: A list of string arguments passed directly to pyright, e.g.
            ["src/", "--warnings"]. Pass an empty list or omit to type-check
            the current directory.

    Returns:
        A structured string containing the exit code, stdout, and stderr.
    """
    return _run(["uv", "run", "pyright", "--outputjson", *(args or [])])


if __name__ == "__main__":
    mcp.run()
