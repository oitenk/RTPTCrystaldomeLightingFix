#!/bin/sh
# Test-compiles the mod's scripts outside the game folder, with the game's own compiler and a copy
# of the vanilla script cache (kept in _archive, which is never published).
# Run from Git Bash:  sh tools/compile.sh
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N="$ROOT/_archive/scc"
GAME="/c/Games/steamapps/common/Cyberpunk 2077"
VANILLA="$ROOT/_archive/vanilla-final.redscripts"
mkdir -p "$N/r6/scripts" "$N/cache"
# The game's final.redscripts is the vanilla cache (redscript writes the modded one to final.redscripts.modded).
[ -f "$VANILLA" ] || cp "$GAME/r6/cache/final.redscripts" "$VANILLA"
rm -rf "$N/r6/scripts/CrystalDomeLightingFix"
cp -r "$ROOT/r6/scripts/CrystalDomeLightingFix" "$N/r6/scripts/"
cp "$VANILLA" "$N/cache/final.redscripts"
rm -f "$N/cache/final.redscripts.bk" "$N/cache/final.redscripts.ts" "$N/cache/final.redscripts.modded"
"$GAME/engine/tools/scc.exe" -compile "$(cygpath -w "$N/r6/scripts")" -customCacheDir "$(cygpath -w "$N/cache")" 2>&1 | grep -v -E "^\s*$|[.]reds$" | tail -40
