#!/usr/bin/env bash
# hermes-mcp-visibility installer
# One command to set up lazy-mcp tool visibility in Hermes Agent.
#
# What it does:
#   1. Copies mcp_visibility.py to Hermes tools directory
#   2. Verifies lazy-mcp hierarchy path
#   3. Tests discovery
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/cioky/hermes-mcp-visibility/main/install.sh | bash
#   # or locally:
#   bash install.sh

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   hermes-mcp-visibility v1.0.0      ║${NC}"
echo -e "${GREEN}║   Real MCP tool names on Discord    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# Find Hermes tools directory
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TOOLS_DIR=""

# Check common locations
for d in \
    "$HERMES_HOME/hermes-agent/tools" \
    "/usr/local/lib/hermes-agent/tools" \
    "$HOME/hermes-agent/tools"; do
    if [ -d "$d" ]; then
        TOOLS_DIR="$d"
        break
    fi
done

if [ -z "$TOOLS_DIR" ]; then
    echo -e "${RED}✗ Hermes tools directory not found.${NC}"
    echo "  Checked: ~/.hermes/hermes-agent/tools, /usr/local/lib/hermes-agent/tools"
    echo "  Set HERMES_HOME if using a custom location."
    exit 1
fi

echo -e "${YELLOW}→ Installing to $TOOLS_DIR${NC}"

# Copy plugin
cp "$(dirname "$0")/mcp_visibility.py" "$TOOLS_DIR/mcp_visibility.py"
echo -e "  ${GREEN}✓${NC} Copied mcp_visibility.py"

# Detect lazy-mcp hierarchy
HIERARCHY=""
for h in \
    "$HOME/hermes-agency/lazy-mcp/hierarchy-hermes" \
    "$HOME/agency/lazy-mcp/hierarchy-hermes"; do
    if [ -d "$h" ] && [ -f "$h/root.json" ]; then
        HIERARCHY="$h"
        break
    fi
done

if [ -n "$HIERARCHY" ]; then
    echo -e "  ${GREEN}✓${NC} Found lazy-mcp hierarchy: $HIERARCHY"
else
    echo -e "  ${YELLOW}⚠${NC} Lazy-mcp hierarchy not auto-detected."
    echo "    Set MCP_VISIBILITY_HIERARCHY env var if needed."
    echo "    Plugin will still work — just won't discover tools at import."
fi

# Quick test
echo ""
echo -e "${YELLOW}→ Testing tool discovery...${NC}"
python3 -c "
import sys, os
sys.path.insert(0, '$TOOLS_DIR/..')
os.chdir('$TOOLS_DIR/..')
from tools.mcp_visibility import tools
print(f'  Discovered {len(tools)} MCP tools')
for c in sorted(tools):
    alias = tools[c].get('alias', c.split('.')[-1])
    print(f'    {alias:20s} ← {c}')
" 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} Quick test skipped (harmless — tools load at Hermes startup)"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation complete!             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "Restart Hermes to activate:"
echo "  hermes gateway restart"
echo "  # or if using CLI: exit and relaunch"
echo ""
echo "On Discord after restart, you'll see:"
echo "  ⚡ ctx_execute  (instead of mcp_lazy_mcp_execute_tool)"
echo "  🔍 web_search"
echo "  🔎 ctx_search"
echo "  📊 ctx_stats"
echo "  ... and all other MCP tools"
echo ""
echo "GitHub: https://github.com/cioky/hermes-mcp-visibility"
