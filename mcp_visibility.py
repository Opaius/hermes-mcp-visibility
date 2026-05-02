#!/usr/bin/env python3
"""
mcp-visibility — Real MCP tool names on Discord for Hermes Agent

Auto-discovers tools from lazy-mcp proxy and registers them as
native Hermes tools with clean, short names.

Key features:
- Dynamic discovery: scans lazy-mcp hierarchy, registers every tool found
- Security-aware: pipes shell commands through Hermes approval system
- Transport-agnostic: works with or without lazy-mcp proxy
- Plugin-agnostic: provides pre_tool_call hook for bare MCP protection

Install:
  hermes plugins install https://github.com/cioky/hermes-mcp-visibility
"""
import json, logging, os, re, subprocess, tempfile
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Path to lazy-mcp hierarchy (auto-detected or set via env)
LAZY_MCP_HIERARCHY = os.path.expanduser(
    os.getenv("MCP_VISIBILITY_HIERARCHY",
              os.path.expanduser("~/hermes-agency/lazy-mcp/hierarchy-hermes"))
)

# Short preferred names for well-known MCP tools
TOOL_ALIASES = {
    "context-mode.ctx_execute": "ctx_execute",
    "context-mode.ctx_search": "ctx_search",
    "context-mode.ctx_index": "ctx_index",
    "context-mode.ctx_fetch_and_index": "ctx_fetch",
    "context-mode.ctx_batch_execute": "ctx_batch",
    "context-mode.ctx_stats": "ctx_stats",
    "context-mode.ctx_doctor": "ctx_doctor",
    "context-mode.ctx_upgrade": "ctx_upgrade",
    "context-mode.ctx_purge": "ctx_purge",
    "context-mode.ctx_insight": "ctx_insight",
    "context-mode.ctx_execute_file": "ctx_exec_file",
    "searxng.search": "web_search",
    "searxng.searxng_web_search": "web_search",
    "searxng.web_url_read": "web_read",
}

TOOL_EMOJIS = {
    "ctx_execute": "⚡", "ctx_search": "🔎", "ctx_index": "📚",
    "ctx_fetch": "📥", "ctx_stats": "📊", "ctx_doctor": "🏥",
    "web_search": "🔍", "web_read": "📖",
}

# Tools whose shell commands need security checks
SHELL_EXEC_TOOLS = {"context-mode.ctx_execute", "context-mode.ctx_batch_execute"}


def _load_hierarchy_tools() -> Dict[str, Dict[str, Any]]:
    """Scan hierarchy dir, return {canonical_name: {server, tool, schema, desc}}."""
    tools = {}
    root = Path(LAZY_MCP_HIERARCHY)
    if not root.is_dir():
        logger.warning("mcp-visibility: %s not found", LAZY_MCP_HIERARCHY)
        return tools

    for srv_dir in sorted(root.iterdir()):
        if not srv_dir.is_dir():
            continue
        server = srv_dir.name
        for tf in sorted(srv_dir.glob("*.json")):
            try:
                data = json.loads(tf.read_text())
            except Exception:
                continue
            for tname, tdef in data.get("tools", {}).items():
                mcp_tool = tdef.get("maps_to", tname)
                canonical = f"{server}.{mcp_tool}"
                tools[canonical] = {
                    "server": server,
                    "tool": mcp_tool,
                    "schema": tdef.get("inputSchema", {}),
                    "desc": tdef.get("description", ""),
                }
    
    logger.info("mcp-visibility: found %d tools from %s", len(tools), LAZY_MCP_HIERARCHY)
    return tools


def _check_command_security(shell_code: str) -> Optional[str]:
    """
    Run Hermes security checks on a shell command.
    Returns None if safe, or an error message string if blocked.
    
    Uses Hermes' built-in dangerous command detection + tirith.
    Falls back gracefully if Hermes runtime isn't available.
    """
    try:
        from tools.approval import check_all_command_guards
        result = check_all_command_guards(shell_code, "local")
        if not result.get("approved"):
            return json.dumps({
                "output": "",
                "exit_code": -1,
                "error": result.get("message", "Command blocked by security policy"),
                "status": result.get("status", "blocked"),
            }, ensure_ascii=False)
        return None  # Approved
    except ImportError:
        # Hermes runtime not available — skip security (standalone/testing)
        logger.debug("mcp-visibility: Hermes approval module not available, skipping security")
        return None
    except Exception as e:
        logger.warning("mcp-visibility: security check failed: %s", e)
        # Fail open in standalone mode, but block with message if possible
        return json.dumps({
            "output": "",
            "exit_code": -1,
            "error": f"Security check error: {e}",
            "status": "blocked",
        }, ensure_ascii=False)


def _execute_direct(shell_code: str, timeout: int = 30) -> str:
    """
    Execute a shell command directly (without lazy-mcp proxy).
    Used as fallback when lazy-mcp is unavailable.
    Still runs security checks first.
    """
    # Security check
    block = _check_command_security(shell_code)
    if block:
        return block

    try:
        result = subprocess.run(
            ["bash", "-c", shell_code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return json.dumps({
            "output": output,
            "exit_code": result.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({
            "output": "",
            "exit_code": -1,
            "error": f"Command timed out after {timeout}s",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "output": "",
            "exit_code": -1,
            "error": str(e),
        }, ensure_ascii=False)


def _call_mcp(server: str, tool: str, args: Dict[str, Any],
              use_proxy: bool = True) -> str:
    """
    Route a tool call with security checks.
    
    With lazy-mcp proxy: check security → route through proxy.
    Without lazy-mcp proxy: check security → execute directly.
    """
    canonical = f"{server}.{tool}"

    # Security check for shell execution tools
    if canonical in SHELL_EXEC_TOOLS:
        language = args.get("language", "")
        code = args.get("code", "")
        if language == "shell" and code:
            block_msg = _check_command_security(code)
            if block_msg:
                return block_msg

    if use_proxy:
        try:
            from model_tools import handle_function_call
            result = handle_function_call("mcp_lazy_mcp_execute_tool", {
                "tool_path": canonical,
                "arguments": args,
            })
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("content", result.get("result", json.dumps(result)))
            return str(result)
        except ImportError:
            logger.debug("mcp-visibility: lazy-mcp proxy unavailable, falling back to direct")
            use_proxy = False

    # Direct execution fallback
    if canonical in SHELL_EXEC_TOOLS:
        return _execute_direct(args.get("code", ""),
                              timeout=args.get("timeout", 30000) // 1000)

    return json.dumps({
        "output": "",
        "exit_code": -1,
        "error": f"Tool {canonical} requires lazy-mcp proxy or direct handler",
    }, ensure_ascii=False)


def _safe_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s).strip('_') or "mcp"


# ── pre_tool_call hook for bare mcp_lazy_mcp_execute_tool ──────────────────

def pre_tool_call_security(tool_name: str, tool_args: dict, **kwargs) -> Optional[dict]:
    """
    pre_tool_call hook that adds security checks to bare MCP calls.
    
    When mcp-visibility plugin ISN'T installed but someone uses
    mcp_lazy_mcp_execute_tool directly, this hook catches shell commands
    and runs security checks.
    
    Returns None to allow the call, or a dict with 'block' key to stop it.
    """
    if tool_name != "mcp_lazy_mcp_execute_tool":
        return None

    tool_path = tool_args.get("tool_path", "")
    if tool_path not in SHELL_EXEC_TOOLS:
        return None

    arguments = tool_args.get("arguments", {})
    language = arguments.get("language", "")
    code = arguments.get("code", "")

    if language == "shell" and code:
        block_msg = _check_command_security(code)
        if block_msg:
            return {"block": True, "reason": block_msg}

    return None


# ── Registration ────────────────────────────────────────

def register_standalone():
    """Register all discovered tools using tools.registry (drop-in mode)."""
    from tools.registry import registry

    tools = _load_hierarchy_tools()
    if not tools:
        return 0

    for canonical, info in sorted(tools.items()):
        display = TOOL_ALIASES.get(canonical)
        if not display:
            parts = canonical.split(".")
            if len(parts) == 2 and parts[1].startswith("ctx_"):
                display = parts[1]
            else:
                display = _safe_name(parts[-1] if len(parts) > 1 else canonical)
        
        emoji = TOOL_EMOJIS.get(display, "🔌")
        server = info["server"]
        tool = info["tool"]
        schema = info["schema"] or {"type": "object", "properties": {}}
        desc = info["desc"] or f"MCP: {canonical}"

        tool_schema = {
            "name": display,
            "description": f"[{canonical}] {desc[:300]}",
            "parameters": schema if schema.get("properties") else {
                "type": "object",
                "properties": {
                    "arguments": {"type": "object", "description": f"Args for {canonical}"}
                }
            }
        }

        def _handler(srv=server, tl=tool):
            def h(args, **kw):
                return _call_mcp(srv, tl, args)
            return h

        try:
            registry.register(
                name=display,
                toolset="hermes-cli",
                schema=tool_schema,
                handler=_handler(),
                emoji=emoji,
            )
        except Exception as e:
            logger.warning("mcp-visibility: skip %s: %s", display, e)

    logger.info("mcp-visibility (standalone): registered %d tools", len(tools))
    return len(tools)


# Auto-register when imported directly (standalone drop-in mode)
_imported_as = __name__
if _imported_as == "__main__" or _imported_as.endswith(".mcp_visibility"):
    try:
        import tools.registry  # noqa: F401
        count = register_standalone()
    except ImportError:
        pass
