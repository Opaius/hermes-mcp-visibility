# hermes-mcp-visibility

Hermes Agent plugin for MCP tool optimization. Hooks-only architecture — works **with or without** context-mode MCP server.

## What it does

| Feature | Effect | Env toggle |
|---------|--------|------------|
| **Security guardrail** | Blocks dangerous shell commands in `ctx_execute` | `MCP_VISIBILITY_SECURITY=1` |
| **Schema compaction** | Truncates MCP tool descriptions (≤140 chars) | `MCP_VISIBILITY_SCHEMA_COMPACT=1` |
| **TOON conversion** | JSON→compact format (40-60% token savings) | `MCP_VISIBILITY_TOON=1` |
| **Result caching** | Deduplicates identical tool calls | `MCP_VISIBILITY_CACHE=1` |

All features default ON. Disable any with env var `=0`.

## Architecture

**Hooks-only** — no wrapper tools registered. Modifies native MCP tools in-place:

- `pre_tool_call` hook → security check on shell commands
- `pre_llm_call` hook (one-shot) → compact tool descriptions + wrap handlers
- `post_tool_call` hook → TOON conversion + caching

Works with direct MCP servers (`bunx -y context-mode`), lazy-mcp proxy, or no MCP at all. Gracefully skips missing tools.

## Install

```bash
# Clone
git clone https://github.com/Opaius/hermes-mcp-visibility.git
cd hermes-mcp-visibility

# Copy plugin
mkdir -p ~/.hermes/plugins/mcp-visibility
cp __init__.py mcp_visibility.py plugin.yaml ~/.hermes/plugins/mcp-visibility/

# Enable in config.yaml
# plugins:
#   enabled:
#     - mcp-visibility

# Restart gateway
hermes gateway restart
```

Or use the install script:
```bash
bash install.sh
```

## Standalone (no MCP)

Plugin works without any MCP server. Security, caching, and TOON features activate for any `mcp_*` tool calls. Schema compaction silently skips unregistered tools.

## With context-mode

When context-mode is configured as MCP server, plugin additionally:
- Compacts verbose tool descriptions before LLM sees them
- Wraps `ctx_execute`/`ctx_batch_execute` handlers with approval-aware security
- Caches and converts results from all MCP tools

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin entry — `register(ctx)`, hooks, schema maps |
| `mcp_visibility.py` | Core: security, caching, TOON, compaction, discovery |
| `plugin.yaml` | Hermes plugin manifest |
| `install.sh` | One-line installer |

## Requirements

- Hermes Agent with plugin support
- Python 3.10+
- Optional: `pyyaml` (for config.yaml discovery)
- Optional: `tools.approval` (Hermes built-in, for security checks)
