#!/bin/sh
# Install warrant into OpenCode and/or Codex from this checkout.
#
#   ./scripts/install.sh --opencode            # global: ~/.config/opencode
#   ./scripts/install.sh --opencode --project  # this project: ./.opencode
#   ./scripts/install.sh --codex               # Codex plugin (skill + hooks) via codex plugin add
#
# Claude Code users: /plugin marketplace add ItsShreyamHere/warrant
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENCODE=0; CODEX=0; PROJECT=0
for a in "$@"; do
  case "$a" in
    --opencode) OPENCODE=1 ;;
    --codex) CODEX=1 ;;
    --project) PROJECT=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done
[ $OPENCODE = 0 ] && [ $CODEX = 0 ] && { sed -n '2,9p' "$0"; exit 2; }

PY=""
for p in python3 python py; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c "import sys; sys.exit(sys.version_info < (3, 10))" 2>/dev/null; then PY="$p"; break; fi
done
[ -z "$PY" ] && { echo "warrant needs Python 3.10+ on PATH" >&2; exit 1; }

if [ $OPENCODE = 1 ]; then
  if [ $PROJECT = 1 ]; then DEST="$PWD/.opencode"; else DEST="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"; fi
  mkdir -p "$DEST/skills" "$DEST/commands" "$DEST/plugin"
  rm -rf "$DEST/plugins/warrant"  # older layout
  rm -rf "$DEST/skills/warrant" && cp -r "$ROOT/skills/warrant" "$DEST/skills/warrant"
  cp "$ROOT"/integrations/opencode/commands/*.md "$DEST/commands/"
  # bake this checkout's absolute path into the plugin (handles Windows paths and spaces)
  "$PY" - "$ROOT" "$ROOT/integrations/opencode/plugin/index.js" "$DEST/plugin/warrant.js" <<'PYEOF'
import json, os, sys
root, src, dst = sys.argv[1:4]
if os.name == "nt" and root.startswith("/") and len(root) > 2 and root[2] == "/":
    root = root[1].upper() + ":" + root[2:]  # /c/Users -> C:/Users (Git Bash)
code = open(src, encoding="utf-8").read().replace('"__WARRANT_ROOT__"', json.dumps(root))
open(dst, "w", encoding="utf-8").write(code)
PYEOF
  echo "OpenCode: skill, /warrant-* commands and hooks plugin installed in $DEST"
fi

if [ $CODEX = 1 ]; then
  command -v codex >/dev/null 2>&1 || { echo "codex not on PATH" >&2; exit 1; }
  codex plugin marketplace add "$ROOT" --enable plugins
  codex plugin add warrant@warrant --enable plugins
  echo "Codex: plugin installed. Turn plugins on (features.plugins = true in ~/.codex/config.toml),"
  echo "       then open /hooks in Codex once to review and trust warrant's hooks."
fi

echo "Then, in a research project:  $PY \"$ROOT/bin/warrant.py\" init \"<your research question>\""
