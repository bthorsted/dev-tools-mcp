# Dev Tools MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes common Python development tools as callable tools, built with the
high-level [`FastMCP`](https://github.com/modelcontextprotocol/python-sdk) API.

## Tools

| Tool | Command run | Description |
|------|-------------|-------------|
| `run_pytest` | `pytest --json-report [args...]` | Run the test suite; the JSON report is appended to the response. |
| `run_ruff_check` | `ruff check --output-format json [args...]` | Lint, emitting JSON diagnostics. |
| `run_ruff_format` | `ruff format [args...]` | Format code (or `--check`). |
| `run_pyright` | `pyright --outputjson [args...]` | Static type checking, emitting JSON. |

Every tool accepts a single parameter, `args: list[str]` — a flexible list of
string arguments (paths, flags like `-k`, `-m`, `--fix`, `--select`, etc.).
Each tool runs its command via `subprocess.run(..., capture_output=True,
text=True)` and returns a structured string containing the **exit code**,
**stdout**, and **stderr**.

### Optimized output formats for agent ingestion

Several tools prepend hardcoded flags to produce machine-friendly output. Your
`args` always come **after** these defaults, so you can override them:

- **`run_ruff_check`** prepends `--output-format json`, so ruff emits a JSON
  array of diagnostic objects instead of the human-readable "full" format with
  code excerpts. Pass your own `--output-format ...` to override.
- **`run_pyright`** prepends `--outputjson`, so pyright emits a structured JSON
  object with a `generalDiagnostics` array instead of plain text.
- **`run_pytest`** prepends `--json-report` (via the
  [`pytest-json-report`](https://pypi.org/project/pytest-json-report/) plugin)
  and directs the report to a temporary file. That file is read back and its
  contents are appended to the response under a `JSON report:` section, so the
  caller receives the structured report directly. The report includes a
  `tests` array with each test's outcome, duration, and failure details.
  (Note: the plugin's `--json-report-file=-` does *not* stream to stdout — it
  would create a stray file literally named `-` — so a temp file is used
  instead.)
- **`run_ruff_format`** has no hardcoded flags.

## Installation

```bash
pip install "mcp[cli]"
```

The underlying dev tools you want to invoke must also be installed and available
on your `PATH` (any subset is fine):

```bash
pip install pytest pytest-json-report ruff pyright
```

Alternatively, install this project itself (which pulls in `mcp[cli]`):

```bash
pip install .
```

## Running the server

```bash
python server.py
```

This starts the MCP server over stdio, ready to be connected to an MCP client.

## Claude Desktop / MCP client configuration

Add the following to your MCP client configuration. For Claude Desktop, edit
`claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dev-tools": {
      "command": "python",
      "args": ["/home/ubuntu/dev-tools-mcp/server.py"]
    }
  }
}
```

Adjust the path to `server.py` to match your installation. Restart the client
afterwards so it picks up the new server.

## Example tool calls

Once connected, an MCP client (or LLM) can call the tools like this:

- **Run the whole test suite:**
  ```json
  { "tool": "run_pytest", "args": { "args": [] } }
  ```

- **Run a specific test by keyword in a directory:**
  ```json
  { "tool": "run_pytest", "args": { "args": ["src/", "-k", "test_login"] } }
  ```

- **Lint and auto-fix a directory:**
  ```json
  { "tool": "run_ruff_check", "args": { "args": ["src/", "--fix"] } }
  ```

- **Check formatting without writing changes:**
  ```json
  { "tool": "run_ruff_format", "args": { "args": ["src/", "--check"] } }
  ```

- **Type-check with warnings:**
  ```json
  { "tool": "run_pyright", "args": { "args": ["src/", "--warnings"] } }
  ```

### Example response

```
Exit code: 0
stdout:
===== 12 passed in 0.34s =====

stderr:
```

## Notes

- If a requested tool executable (e.g. `pyright`) is not installed, the server
  returns a clear `Command not found` message with exit code `127` rather than
  crashing.
- The server never raises on non-zero exit codes; the exit code is always
  reported in the response so the caller can decide how to react.
