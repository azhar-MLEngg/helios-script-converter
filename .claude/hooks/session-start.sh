#!/bin/bash
set -euo pipefail

# Only run in remote/web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Copy project CLAUDE.md to global ~/.claude/CLAUDE.md
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
SOURCE="$REPO_ROOT/CLAUDE.md"

if [ -f "$SOURCE" ]; then
  mkdir -p ~/.claude
  cp "$SOURCE" ~/.claude/CLAUDE.md
fi
