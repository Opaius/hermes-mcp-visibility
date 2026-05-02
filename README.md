# hermes-mcp-visibility

MCP tool optimization plugin — **Hermes Agent** + **OpenCode** support. Single codebase, two plugins, same pipeline.

## What it does

| Feature | Hermes | OpenCode | Description |
|---------|:---:|:---:|-------------|
| **Security guardrail** | ✓ | ✗¹ | Blocks dangerous shell commands, evasion detection, audit logging |
| **Smart formatting** | ✓ | ✓ | JSON→md-table, YAML, HTML strip, text truncation with `[vis fmt=...]` headers |
| **Schema compaction** | ✓ | ✗² | Truncates MCP tool descriptions ≤140 chars before LLM sees them |
| **Result caching** | ✓ | ✓ | Deduplicates identical tool calls (file-based, TTL-aware) |
| **TOON fallback** | ✓ | ✓ | Legacy compact format via `MCP_VISIBILITY_FMT=toon` |

¹ OpenCode has built-in permission system — no need for plugin security.  
² OpenCode MCP tools already have compact descriptions.

## Architecture

```
Hermes Agent                     OpenCode
    │                                │
    ├─ pre_tool_call hook            ├─ tool.execute.before
    │  └─ security check (shell)     │  └─ cache check
    ├─ pre_llm_call hook (one-shot)  │
    │  ├─ compact tool descriptions  │
    │  └─ wrap handlers (security+fmt)│
    └─ post_tool_call hook           └─ tool.execute.after
       └─ format + cache                └─ format + cache
```

**Shared modules:**
- `security.py` — unified security (hardline/approval/evasion patterns, audit logging)
- `output_fmt.py` — smart formatting (md-table, YAML, truncation, HTML strip)
- `mcp_visibility.py` — core: TOON, cache, discovery, schema compaction

## Install

### Hermes Agent

```bash
git clone https://github.com/Opaius/hermes-mcp-visibility.git
mkdir -p ~/.hermes/plugins/mcp-visibility
cp hermes-mcp-visibility/{__init__.py,mcp_visibility.py,security.py,output_fmt.py,plugin.yaml} ~/.hermes/plugins/mcp-visibility/
hermes gateway restart
```

Or: `bash install.sh`

### OpenCode

```bash
git clone https://github.com/Opaius/hermes-mcp-visibility.git
cp hermes-mcp-visibility/opencode-plugin.ts ~/.config/opencode/plugins/mcp-visibility.ts
```

Already in config? Just update the file. OpenCode picks it up on next run.

## Configuration

### Env vars (both plugins)

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_VISIBILITY_SECURITY` | `1` | Security checks (Hermes only) |
| `MCP_VISIBILITY_CACHE` | `1` | Result caching |
| `MCP_VISIBILITY_FMT` | `smart` | Format mode: `smart` \| `toon` \| `passthrough` |
| `MCP_VISIBILITY_TOON` | `1` | Legacy TOON toggle (overridden by `FMT`) |
| `MCP_VISIBILITY_SCHEMA_COMPACT` | `1` | Schema compaction (Hermes only) |

Set in `~/.hermes/.env` for Hermes, or process env for OpenCode.

### Smart formatting modes

```
smart (default)    md-table for arrays ≤8 cols, YAML for dicts, truncate long text
toon              Legacy compact format
passthrough       Raw output, no formatting
```

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Hermes plugin entry — `register(ctx)`, hooks, schema maps |
| `mcp_visibility.py` | Core: TOON, caching, discovery, schema compaction |
| `security.py` | Unified security module (hardline/approval/evasion, audit) |
| `output_fmt.py` | Smart formatting (md-table, YAML, truncation, HTML strip) |
| `opencode-plugin.ts` | OpenCode plugin (formatting + cache only) |
| `plugin.yaml` | Hermes plugin manifest |
| `install.sh` | One-line installer for Hermes |
| `test_security.py` | 32 security tests |
| `test_output_fmt.py` | 14 formatting tests |

## Verifying

```bash
# Hermes: check logs
grep "mcp-visibility" ~/.hermes/logs/agent.log | tail -5

# OpenCode: run a quick test
opencode run "echo test" --dangerously-skip-permissions

# Run tests
cd hermes-mcp-visibility
python3 test_security.py    # 32 tests
python3 test_output_fmt.py  # 14 tests
```

## Requirements

- Hermes Agent with plugin support
- Python 3.10+ (PyYAML optional)
- Bun (OpenCode plugin)
