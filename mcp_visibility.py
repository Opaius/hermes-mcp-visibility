#!/usr/bin/env python3
"""
mcp-visibility — Real MCP tool names on Discord for Hermes Agent

Auto-discovers tools from lazy-mcp proxy and registers them as
native Hermes tools with clean, short names. Instead of seeing
'mcp_lazy_mcp_execute_tool' × N on Discord, you see the actual
tool: ctx_execute, web_search, ctx_search, etc.

Dynamic: add MCP servers → restart Hermes → tools appear.
No config. No code changes. Just drop the file in tools/.

Install:
  cp mcp_visibility.py ~/.hermes/hermes-agent/tools/
  # or: hermes plugins install https://github.com/cioky/hermes-mcp-visibility
"""
import json, logging, os, re
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

from tools.registry import registry

# Path to lazy-mcp hierarchy (auto-detected or set via env)
LAZY_MCP_HIERARCHY = os.path.expanduser(
    os.getenv("MCP_VISIBILITY_HIERARCHY",
              os.path.expanduser("~/hermes-agency/lazy-mcp/hierarchy-hermes"))
)

# Short preferred names for well-known MCP tools
# Format: "server.tool" → "display_name"
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
    
    logger.info("mcp-visibility: found %d tools", len(tools))
    return tools


def _call_mcp(server: str, tool: str, args: Dict[str, Any]) -> str:
    """Route through lazy-mcp proxy."""
    from model_tools import handle_function_call
    result = handle_function_call("mcp_lazy_mcp_execute_tool", {
        "tool_path": f"{server}.{tool}",
        "arguments": args,
    })
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("content", result.get("result", json.dumps(result)))
    return str(result)


def _safe_name(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s).strip('_') or "mcp"


# ── Registration ────────────────────────────────────────

tools = _load_hierarchy_tools()

for canonical, info in sorted(tools.items()):
    # Prefer alias, fall back to canonical
    display = TOOL_ALIASES.get(canonical)
    if not display:
        # Auto-generate: strip ctx_ prefix for context-mode, keep short
        parts = canonical.split(".")
        if len(parts) == 2 and parts[1].startswith("ctx_"):
            display = parts[1]  # ctx_execute, ctx_search, etc.
        else:
            display = _safe_name(parts[-1] if len(parts) > 1 else canonical)
    
    emoji = TOOL_EMOJIS.get(display, "🔌")
    server = info["server"]
    tool = info["tool"]
    schema = info["schema"] or {"type": "object", "properties": {}}
    desc = info["desc"] or f"MCP: {canonical}"

    # Build schema with info about the underlying tool
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

    # Closure to capture server/tool
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

logger.info("mcp-visibility: registered %d tools", len(tools))
