#!/usr/bin/env bash
# Install or update the shipped global rules into the user's ~/.claude/CLAUDE.md.
#
# Default mode is a marker-based merge: the template is written between
# comment markers, so re-running updates that block in place and never
# touches rules the user wrote themselves.
#
# Usage:
#   scripts/install_global_claude.sh              # merge (idempotent)
#   scripts/install_global_claude.sh --overwrite  # replace the whole file
#   scripts/install_global_claude.sh --dry-run    # show what would happen
#
# CLAUDE_HOME overrides ~/.claude (useful for sandboxed/test runs).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_DIR/global/CLAUDE.md"
DEST_DIR="${CLAUDE_HOME:-$HOME/.claude}"
DEST="$DEST_DIR/CLAUDE.md"
START="<!-- my_ai_skills:global-rules:start -->"
END="<!-- my_ai_skills:global-rules:end -->"

MODE="merge"
case "${1:-}" in
  --overwrite) MODE="overwrite" ;;
  --dry-run)   MODE="dry-run" ;;
  "")          ;;
  *) echo "error: unknown option '$1' (use --overwrite or --dry-run)" >&2; exit 1 ;;
esac

[[ -f "$SRC" ]] || { echo "error: template not found: $SRC" >&2; exit 1; }

marked_block() {
  printf '%s\n' "$START"
  cat "$SRC"
  printf '%s\n' "$END"
}

plan() {
  if [[ ! -f "$DEST" ]]; then
    echo "create"
  elif [[ "$MODE" == "overwrite" ]]; then
    echo "overwrite"
  elif grep -qF "$START" "$DEST"; then
    echo "update-block"
  else
    echo "append-block"
  fi
}

ACTION="$(plan)"

if [[ "$MODE" == "dry-run" ]]; then
  echo "would $ACTION $DEST (template: $SRC)"
  exit 0
fi

mkdir -p "$DEST_DIR"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

case "$ACTION" in
  create|overwrite)
    marked_block > "$TMP"
    ;;
  update-block)
    awk -v start="$START" -v end="$END" -v src="$SRC" '
      $0 == start { print; while ((getline line < src) > 0) print line; print end; skip = 1; next }
      $0 == end   { skip = 0; next }
      !skip       { print }
    ' "$DEST" > "$TMP"
    ;;
  append-block)
    { cat "$DEST"; echo ""; marked_block; } > "$TMP"
    ;;
esac

mv "$TMP" "$DEST"
trap - EXIT
echo "$ACTION: $DEST"
echo "Rules from this repo live between the '$START' markers; re-run this script after pulling updates."
