#!/usr/bin/env sh
# macOS/Linux installer. Usage: ./install.sh [claude|cursor|codex|project]
set -e
T=${1:-claude}; HERE=$(cd "$(dirname "$0")" && pwd)
case "$T" in claude) D="$HOME/.claude/skills";; cursor) D="$HOME/.cursor/skills";; codex) D="$HOME/.codex/skills";; project) D="$PWD/.claude/skills";; *) echo "unknown target $T"; exit 1;; esac
mkdir -p "$D"
rm -rf "$D/skill-shipper" && cp -R "$HERE/free/skill-shipper" "$D/" && echo "Installed Hephaestus of Skills (skill-shipper) -> $D"
