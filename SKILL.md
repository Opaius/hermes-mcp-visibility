---
name: mcp-visibility
description: MCP optimization plugin for Hermes Agent + OpenCode — smart formatting, security guardrails, schema compaction, result caching.
version: 2.0.0
author: cioky
---

# mcp-visibility v2

Dual plugin: Hermes Agent + OpenCode. Same pipeline, two transports.

**Installed at:** `~/.hermes/plugins/mcp-visibility/` (Hermes) and `~/.config/opencode/plugins/mcp-visibility.ts` (OpenCode)

## Features

- **Smart formatting:** JSON→markdown table, YAML, HTML strip, text truncation
- **Security:** hardline/approval/evasion patterns (Hermes only)
- **Schema compaction:** ≤140 char descriptions (Hermes only)
- **Result caching:** file-based, TTL-aware
- **TOON fallback:** via `MCP_VISIBILITY_FMT=toon`

## Key files

- `security.py` — unified security module
- `output_fmt.py` — smart formatting engine
- `opencode-plugin.ts` — OpenCode plugin (formatting + cache)

## Pitfalls

- Gateway restart needed after plugin code change
- `MCP_VISIBILITY_SECURITY=0` disables ALL security (Hermes)
- OpenCode uses native permissions — plugin security stripped
