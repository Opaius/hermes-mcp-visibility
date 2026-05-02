# hermes-mcp-visibility

Real MCP tool names on Discord for Hermes Agent.

**Problem:** When using lazy-mcp proxy, Discord shows `mcp_lazy_mcp_execute_tool` repeated for every MCP call. You can't tell which tool is being used.

**Solution:** This plugin auto-discovers all MCP tools from the lazy-mcp proxy and registers them as native Hermes tools with their real names. After install, Discord shows:

| Before | After |
|--------|-------|
| ⚙️ mcp_lazy_mcp_execute_tool | ⚡ ctx_execute |
| ⚙️ mcp_lazy_mcp_execute_tool | 🔍 web_search |
| ⚙️ mcp_lazy_mcp_execute_tool | 🔎 ctx_search |
| ⚙️ mcp_lazy_mcp_execute_tool | 📊 ctx_stats |
| ⚙️ mcp_lazy_mcp_execute_tool | 📥 ctx_fetch |

## Features

- **Dynamic discovery** — scans lazy-mcp hierarchy, registers every tool found
- **Clean names** — `ctx_execute`, `web_search`, `ctx_fetch`, not `context_mode_ctx_execute`
- **Auto-updating** — add a new MCP server → restart Hermes → tools appear
- **Zero config** — just drop the file in, no YAML editing
- **Tool aliases** — well-known tools get short, memorable names

## Install

```bash
# One-liner
curl -fsSL https://raw.githubusercontent.com/cioky/hermes-mcp-visibility/main/install.sh | bash

# Or manually
cp mcp_visibility.py ~/.hermes/hermes-agent/tools/
hermes gateway restart
```

## Registered tools (13 discovered)

```
ctx_execute      ← context-mode.ctx_execute      ⚡
ctx_search       ← context-mode.ctx_search       🔎
ctx_index        ← context-mode.ctx_index        📚
ctx_fetch        ← context-mode.ctx_fetch_and_index 📥
ctx_batch        ← context-mode.ctx_batch_execute
ctx_stats        ← context-mode.ctx_stats        📊
ctx_doctor       ← context-mode.ctx_doctor       🏥
ctx_upgrade      ← context-mode.ctx_upgrade
ctx_purge        ← context-mode.ctx_purge
ctx_insight      ← context-mode.ctx_insight
ctx_exec_file    ← context-mode.ctx_execute_file
web_search       ← searxng.search                🔍
web_read         ← searxng.web_url_read          📖
```

## Requirements

- Hermes Agent (any recent version)
- [lazy-mcp](https://github.com/cioky/lazy-mcp) proxy configured in `~/.hermes/config.yaml`
- Python 3.10+

## Configuration

Zero config needed. The plugin auto-detects the hierarchy path from:
1. `MCP_VISIBILITY_HIERARCHY` env var
2. `~/hermes-agency/lazy-mcp/hierarchy-hermes`

To add custom tool aliases, edit the `TOOL_ALIASES` dict in `mcp_visibility.py`.

## How it works

```
lazy-mcp proxy
    ↓
hierarchy-hermes/
    context-mode/
        ctx_execute.json  →  {maps_to: "ctx_execute", inputSchema: {...}}
        ctx_search.json   →  {maps_to: "ctx_search", ...}
    searxng/
        search.json       →  {maps_to: "search", ...}
    ↓
mcp_visibility.py (this plugin)
    ↓  auto-discovers all tools
    ↓  registers as Hermes tools with clean names
    ↓
Hermes Agent
    ↓  shows tool names on Discord
⚡ ctx_execute   🔍 web_search   🔎 ctx_search
```

## Uninstall

```bash
rm ~/.hermes/hermes-agent/tools/mcp_visibility.py
# or: rm /usr/local/lib/hermes-agent/tools/mcp_visibility.py
hermes gateway restart
```

## License

MIT — do whatever you want.

---

Part of the [hermes-ctx-enhance](https://github.com/Opaius/hermes-ctx-enhance) ecosystem.
