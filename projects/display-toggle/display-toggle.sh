#!/bin/bash
# Display Toggle - Quickly disconnect/reconnect external display
# Requires: brew install displayplacer
#
# Usage:
#   ./display-toggle.sh          # Toggle external display
#   ./display-toggle.sh list     # List displays
#   ./display-toggle.sh off      # Turn off external
#   ./display-toggle.sh on       # Turn on external

set -e

# Check if displayplacer is installed
if ! command -v displayplacer &> /dev/null; then
    echo "displayplacer not found. Installing via Homebrew..."
    brew install displayplacer
fi

# State file to remember which display was disabled
STATE_FILE="$HOME/.display-toggle-state"

# Get list of displays
get_displays() {
    displayplacer list 2>/dev/null | grep -E "^Persistent|^Resolution|^Type" | head -20
}

# Get external display ID
get_external_id() {
    displayplacer list 2>/dev/null | grep -B5 "Type: external" | grep "Persistent screen id:" | head -1 | awk '{print $4}'
}

# Get internal display ID
get_internal_id() {
    displayplacer list 2>/dev/null | grep -B5 "Type: MacBook built in" | grep "Persistent screen id:" | head -1 | awk '{print $4}'
}

# Check if display is currently enabled
is_enabled() {
    local display_id="$1"
    displayplacer list 2>/dev/null | grep -A10 "$display_id" | grep -q "Resolution:" && echo "true" || echo "false"
}

# Disable external display
disable_external() {
    local ext_id=$(get_external_id)
    if [ -z "$ext_id" ]; then
        echo "❌ No external display found"
        exit 1
    fi
    
    echo "🔌 Disabling external display ($ext_id)..."
    
    # Save the current config for re-enabling
    displayplacer list 2>/dev/null | grep "displayplacer" > "$STATE_FILE"
    echo "$ext_id" >> "$STATE_FILE"
    
    displayplacer "id:$ext_id enabled:false"
    echo "✅ External display disabled"
}

# Enable external display
enable_external() {
    if [ ! -f "$STATE_FILE" ]; then
        echo "❌ No saved state found. Try unplugging and replugging the display."
        exit 1
    fi
    
    local ext_id=$(tail -1 "$STATE_FILE")
    echo "🔌 Re-enabling external display ($ext_id)..."
    
    displayplacer "id:$ext_id enabled:true"
    
    # Restore the full config
    local config=$(head -1 "$STATE_FILE")
    if [ -n "$config" ]; then
        eval "$config" 2>/dev/null || true
    fi
    
    echo "✅ External display enabled"
}

# Toggle external display
toggle_external() {
    local ext_id=$(get_external_id)
    
    if [ -z "$ext_id" ]; then
        # No external found - maybe it's disabled, try to enable
        if [ -f "$STATE_FILE" ]; then
            enable_external
        else
            echo "❌ No external display found"
            exit 1
        fi
    else
        # External found and enabled - disable it
        disable_external
    fi
}

# Main
case "${1:-toggle}" in
    list)
        echo "📺 Connected Displays:"
        echo ""
        get_displays
        echo ""
        echo "External ID: $(get_external_id)"
        echo "Internal ID: $(get_internal_id)"
        ;;
    off|disable)
        disable_external
        ;;
    on|enable)
        enable_external
        ;;
    toggle|*)
        toggle_external
        ;;
esac
