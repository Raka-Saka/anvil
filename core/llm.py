"""
LLM backend - every Claude call in Anvil goes through here.

Default backend is Claude Code (`claude -p`), which runs on the Claude
subscription you are logged into. The Anthropic API (paid per token, needs
credit) is the fallback, or forced with `llm: api` in config/api_keys.yaml.

get_client() returns an object with the same `messages.create(...)` shape as
the Anthropic SDK, so the generators work with either backend unchanged.
"""

import json
import re
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import yaml
except ImportError:
    yaml = None

API_MODEL = "claude-opus-5-5"
CLI_MODEL = "opus"
TIMEOUT = 900  # seconds; long articles take a while

# Isolated run: no CLAUDE.md or settings, no MCP servers, nothing saved. Tools only when asked.
CLI_FLAGS = ["--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
             "--output-format", "json"]


class LLMError(RuntimeError):
    pass


def _config() -> dict:
    path = Path(__file__).parent.parent / "config" / "api_keys.yaml"
    if path.exists() and yaml:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def claude_code_path() -> Optional[str]:
    return shutil.which("claude")


def backend() -> Optional[str]:
    """'claude_code', 'api', or None when neither is usable."""
    from core.config import load_api_key
    wanted = _config().get("llm", "claude_code")
    if wanted == "claude_code" and claude_code_path():
        return "claude_code"
    if load_api_key() and anthropic:
        return "api"
    return "claude_code" if claude_code_path() else None


def describe() -> str:
    b = backend()
    return {"claude_code": "Claude Code (subscription)", "api": "Anthropic API (paid credit)"}.get(b, "none")


# --- Claude Code --------------------------------------------------------------

# his name in katakana is エリソン・フロー; older documents say フローラン, which confuses employers
_WRONG_NAME = re.compile(r"フローラン|ふろーらん")


def fix_names(obj):
    """Every generated text uses フロー, never フローラン (strings, lists and dicts, recursively)."""
    if isinstance(obj, str):
        return _WRONG_NAME.sub(lambda m: "フロー" if m.group(0)[0] == "フ" else "ふろー", obj)
    if isinstance(obj, list):
        return [fix_names(x) for x in obj]
    if isinstance(obj, dict):
        return {k: fix_names(v) for k, v in obj.items()}
    return obj


def run_claude_code(prompt: str, system: Optional[str] = None, schema: Optional[dict] = None,
                    model: str = CLI_MODEL, tools: Optional[list] = None, effort: Optional[str] = None) -> dict:
    """One headless Claude Code turn. Returns the CLI's JSON result."""
    exe = claude_code_path()
    if not exe:
        raise LLMError("Claude Code not found. Install it and run `claude` once to log in.")

    tool_list = ",".join(tools or [])
    args = [exe, "-p", "--model", model, *CLI_FLAGS, "--tools", tool_list]
    if tools:
        args += ["--allowedTools", tool_list]
    if effort:
        args += ["--effort", effort]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    with tempfile.TemporaryDirectory(prefix="anvil_llm_") as tmp:
        if system:
            sys_file = Path(tmp) / "system.txt"
            sys_file.write_text(system, encoding="utf-8")
            args += ["--system-prompt-file", str(sys_file)]
        if schema:
            args += ["--json-schema", json.dumps(schema)]
        try:
            proc = subprocess.run(args, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  cwd=tmp, env=env, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise LLMError(f"Claude Code took longer than {TIMEOUT}s.")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise LLMError((proc.stderr or proc.stdout or "No output from Claude Code").strip()[:300])
    if data.get("is_error"):
        raise LLMError(str(data.get("result") or data.get("subtype") or "Claude Code error")[:300])
    for k in ("result", "structured_output"):
        if k in data:
            data[k] = fix_names(data[k])
    return data


class _Messages:
    def create(self, messages: list, system=None, **_ignored):
        """Anthropic-SDK-shaped call. model/max_tokens are ignored; Claude Code picks the limits."""
        if isinstance(system, list):
            system = "\n\n".join(b.get("text", "") for b in system)
        parts = []
        for m in messages:
            content = m["content"]
            if isinstance(content, list):
                content = "\n\n".join(b.get("text", "") for b in content if b.get("type") == "text")
            parts.append(content if m["role"] == "user" else f"<previous_reply>\n{content}\n</previous_reply>")
        data = run_claude_code("\n\n".join(parts), system=system)
        text = data.get("result") or ""
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=fix_names(text))],
                               stop_reason=data.get("stop_reason"))


class ClaudeCodeClient:
    def __init__(self):
        self.messages = _Messages()


class _ApiClient:
    """Anthropic SDK client that always uses the current model."""

    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self.messages = self

    def create(self, **kw):
        kw["model"] = API_MODEL
        kw.setdefault("max_tokens", 16000)
        return self._client.messages.create(**kw)


def get_client(api_key: Optional[str] = None):
    """Client for the configured backend, or None if Claude is unavailable."""
    b = backend()
    if b == "claude_code":
        return ClaudeCodeClient()
    if b == "api":
        from core.config import load_api_key
        return _ApiClient(api_key or load_api_key())
    return None


def ask_json(prompt: str, system: str, schema: dict) -> dict:
    """Structured answer validated against `schema`."""
    b = backend()
    if b == "claude_code":
        data = run_claude_code(prompt, system=system, schema=schema)
        out = data.get("structured_output")
        if out is None:
            raise LLMError("Claude Code returned no structured output.")
        return out
    if b == "api":
        from core.config import load_api_key
        client = anthropic.Anthropic(api_key=load_api_key())
        response = client.beta.messages.create(
            model=API_MODEL, max_tokens=8000, system=system,
            betas=["server-side-fallback-2026-07-01"],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            extra_body={"fallbacks": "default"},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise LLMError("Claude declined this request.")
        return fix_names(json.loads(next(b.text for b in response.content if b.type == "text")))
    raise LLMError("No Claude backend: install Claude Code or add an API key.")
