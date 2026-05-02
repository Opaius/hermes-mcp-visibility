"""
mcp-visibility — Real MCP tool names on Discord for Hermes Agent.

Auto-discovers all MCP tools from the lazy-mcp proxy and registers them
as native Hermes tools with clean, short names. Instead of seeing
'mcp_lazy_mcp_execute_tool' × N on Discord, users see actual tool names:
ctx_execute, web_search, ctx_search, etc.

Agnostic by design: add a new MCP server → restart Hermes → tools appear.
No config. No hardcoded server list.

Install:
  hermes plugins install https://github.com/cioky/hermes-mcp-visibility
  # or manually:
  git clone https://github.com/cioky/hermes-mcp-visibility \
    ~/.hermes/plugins/mcp-visibility/
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Import core discovery logic from sibling module
from .mcp_visibility import (
    _load_hierarchy_tools,
    _call_mcp,
    TOOL_ALIASES,
    TOOL_EMOJIS,
    _safe_name,
)


def register(ctx) -> None:
    """Register all discovered MCP tools. Called once by plugin loader."""
    tools = _load_hierarchy_tools()
    if not tools:
        logger.warning("mcp-visibility: no MCP tools found in hierarchy")
        return

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

        # Create handler closure capturing server/tool
        def _make_handler(srv, tl):
            def handler(args, **kw):
                return _call_mcp(srv, tl, args)
            return handler

        try:
            ctx.register_tool(
                name=display,
                toolset="mcp-visibility",
                schema=tool_schema,
                handler=_make_handler(server, tool),
                emoji=emoji,
            )
        except Exception as e:
            logger.warning("mcp-visibility: skip %s: %s", display, e)

    logger.info("mcp-visibility: registered %d tools", len(tools))
