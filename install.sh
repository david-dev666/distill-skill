#!/usr/bin/env bash
# distill-skill 安装：复制 skill 到目标目录（默认 Claude skills 目录）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/.claude/skills/distill-skill}"

mkdir -p "$DEST"
cp -R "$ROOT/SKILL.md" "$ROOT/references" "$ROOT/scripts" "$ROOT/assets" "$DEST/"
chmod +x "$DEST/scripts/"*.sh "$DEST/scripts/"*.py

echo "installed -> $DEST"
