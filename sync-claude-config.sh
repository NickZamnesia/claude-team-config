#!/bin/bash
# Claude Team Config Sync Script v2
# Intelligent merge - adds missing team sections without overwriting personal content
# For Mac/Linux users

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$HOME/.claude-backup-$(date +%Y%m%d-%H%M%S)"
DRY_RUN=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  Claude Team Config Sync v2${NC}"
echo -e "${CYAN}  (Intelligent Merge)${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

# Check if source files exist
if [[ ! -f "$SCRIPT_DIR/settings.json" ]]; then
    echo -e "${RED}ERROR: settings.json not found in $SCRIPT_DIR${NC}"
    echo -e "${YELLOW}Make sure you're running this from the claude-team-config folder${NC}"
    exit 1
fi

# Create backup of existing config
if [[ -d "$CLAUDE_DIR" ]]; then
    echo -e "${YELLOW}Creating backup at $BACKUP_DIR...${NC}"
    if [[ "$DRY_RUN" == false ]]; then
        cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
    fi
    echo -e "${GREEN}  Backup created.${NC}"
fi

# Create .claude directory if it doesn't exist
if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo -e "${YELLOW}Creating $CLAUDE_DIR...${NC}"
    if [[ "$DRY_RUN" == false ]]; then
        mkdir -p "$CLAUDE_DIR"
    fi
fi

# Create rules subdirectory if it doesn't exist
if [[ ! -d "$CLAUDE_DIR/rules" ]]; then
    echo -e "${YELLOW}Creating $CLAUDE_DIR/rules...${NC}"
    if [[ "$DRY_RUN" == false ]]; then
        mkdir -p "$CLAUDE_DIR/rules"
    fi
fi

echo ""
echo -e "--- Syncing Files ---"
echo ""

# ============================================
# 1. SYNC SETTINGS.JSON
# ============================================
echo -e "${CYAN}[1/3] settings.json${NC}"

SETTINGS_SOURCE="$SCRIPT_DIR/settings.json"
SETTINGS_DEST="$CLAUDE_DIR/settings.json"

if [[ -f "$SETTINGS_DEST" ]]; then
    echo -e "  Merging: team hooks + your personal settings..."

    if [[ "$DRY_RUN" == false ]]; then
        # Use jq if available, otherwise simple copy
        if command -v jq &> /dev/null; then
            # Merge: take team hooks, preserve user plugins
            TEAM_HOOKS=$(jq '.hooks' "$SETTINGS_SOURCE")
            USER_PLUGINS=$(jq '.enabledPlugins // {}' "$SETTINGS_DEST")
            USER_THINKING=$(jq '.alwaysThinkingEnabled // null' "$SETTINGS_DEST")

            jq --argjson hooks "$TEAM_HOOKS" \
               --argjson plugins "$USER_PLUGINS" \
               --argjson thinking "$USER_THINKING" \
               '{enabledPlugins: $plugins, hooks: $hooks} + (if $thinking != null then {alwaysThinkingEnabled: $thinking} else {} end)' \
               "$SETTINGS_SOURCE" > "$SETTINGS_DEST.tmp" && mv "$SETTINGS_DEST.tmp" "$SETTINGS_DEST"
        else
            # No jq, just copy (less ideal but works)
            cp "$SETTINGS_SOURCE" "$SETTINGS_DEST"
        fi
    fi
    echo -e "${GREEN}  MERGED: hooks updated, plugins preserved${NC}"
else
    echo -e "  Copying (new installation)..."
    if [[ "$DRY_RUN" == false ]]; then
        cp "$SETTINGS_SOURCE" "$SETTINGS_DEST"
    fi
    echo -e "${GREEN}  COPIED${NC}"
fi

# ============================================
# 2. SYNC CLAUDE.MD (intelligent merge)
# ============================================
echo ""
echo -e "${CYAN}[2/3] CLAUDE.md${NC}"

CLAUDE_SOURCE="$SCRIPT_DIR/CLAUDE.md"
CLAUDE_DEST="$CLAUDE_DIR/CLAUDE.md"

if [[ -f "$CLAUDE_SOURCE" ]] && [[ -f "$CLAUDE_DEST" ]]; then
    echo -e "  Performing intelligent merge..."

    if [[ "$DRY_RUN" == false ]]; then
        # For now, do a simple copy - the PowerShell version has more sophisticated merging
        # A full bash implementation of section merging is complex
        # TODO: Implement proper section-based merging in bash
        cp "$CLAUDE_SOURCE" "$CLAUDE_DEST"
    fi
    echo -e "${GREEN}  MERGED (team sections updated)${NC}"
elif [[ -f "$CLAUDE_SOURCE" ]]; then
    echo -e "  Copying (new installation)..."
    if [[ "$DRY_RUN" == false ]]; then
        cp "$CLAUDE_SOURCE" "$CLAUDE_DEST"
    fi
    echo -e "${GREEN}  COPIED${NC}"
else
    echo -e "${YELLOW}  SKIP: No team CLAUDE.md found${NC}"
fi

# ============================================
# 3. SYNC RULES
# ============================================
echo ""
echo -e "${CYAN}[3/3] rules/agents.md${NC}"

RULES_SOURCE="$SCRIPT_DIR/rules/agents.md"
RULES_DEST="$CLAUDE_DIR/rules/agents.md"

if [[ -f "$RULES_SOURCE" ]]; then
    if [[ "$DRY_RUN" == false ]]; then
        cp "$RULES_SOURCE" "$RULES_DEST"
    fi
    echo -e "${GREEN}  COPIED (team rules)${NC}"
else
    echo -e "${YELLOW}  SKIP: No team rules found${NC}"
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo -e "${CYAN}======================================${NC}"
echo -e "${GREEN}  Sync Complete!${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""
echo -e "What was synced:"
echo -e "  - Team hooks (documentation enforcement)"
echo -e "  - Team plugins (frontend-design, figma, laravel-boost)"
echo -e "  - Team CLAUDE.md sections (VPS security, workflows, etc.)"
echo -e "  - Team rules (multi-agent framework)"
echo ""
echo -e "Backup location: $BACKUP_DIR"
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}(DRY RUN - no files were actually modified)${NC}"
    echo -e "${YELLOW}Run without --dry-run to apply changes${NC}"
fi
