"""
mcp-visibility — Real MCP tool names on Discord for Hermes Agent.

Security-aware, transport-agnostic MCP tool wrapper.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from .mcp_visibility import (
    _load_hierarchy_tools,
    _call_mcp,
    _check_command_security,
    _execute_direct,
    SHELL_EXEC_TOOLS,
    TOOL_ALIASES,
    TOOL_EMOJIS,
    _safe_name,
    pre_tool_call_security,
)


def register(ctx) -> None:
    """Register all discovered MCP tools with security + transport agnosticism."""
    tools = _load_hierarchy_tools()
    if not tools:
        logger.warning("mcp-visibility: no MCP tools found in hierarchy")
        return

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

        # Handler with security checks built-in
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

    # Register pre_tool_call hook for bare MCP protection
    # This catches mcp_lazy_mcp_execute_tool calls when the wrapper tools
    # aren't being used, and still applies security checks.
    try:
        ctx.register_hook("pre_tool_call", pre_tool_call_security)
        logger.info("mcp-visibility: registered pre_tool_call security hook")
    except Exception as e:
        logger.debug("mcp-visibility: pre_tool_call hook registration skipped: %s", e)

    logger.info("mcp-visibility: registered %d tools", len(tools))
