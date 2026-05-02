---
name: mcp-visibility
description: "Real MCP tool names on Discord — auto-discovers lazy-mcp tools and registers them as native Hermes tools with clean names."
version: 1.0.0
author: cioky
license: MIT
metadata:
  hermes:
    tags: [mcp, lazy-mcp, discord, tools, visibility, devops]
    homepage: https://github.com/cioky/hermes-mcp-visibility
---

# mcp-visibility

Replaces generic `mcp_lazy_mcp_execute_tool` with real tool names on Discord.

After install, instead of seeing N identical tool bubbles, you see:
- ⚡ `ctx_execute`
- 🔍 `web_search`
- 🔎 `ctx_search`
- 📊 `ctx_stats`

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/cioky/hermes-mcp-visibility/main/install.sh | bash
hermes gateway restart
```

## How it works

Scans `lazy-mcp/hierarchy-hermes/` directory, discovers all MCP tools, and registers each as a Hermes tool with the tool's real name. The underlying MCP call still goes through the lazy-mcp proxy — only the DISPLAYED name changes.

## Requirements

- Hermes Agent with lazy-mcp MCP server configured
- Tool needs to be in Hermes tools directory
