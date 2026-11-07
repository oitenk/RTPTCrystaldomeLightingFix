"""Build dist/CrystalDomeLightingFix.zip from the mod folders (game-root layout).

usage: python -I tools/make_zip.py          release zip
       python -I tools/make_zip.py --test   also includes the CET test hotkey
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [
    "archive/pc/mod/CrystalDomeLightingFix.archive",
    "archive/pc/mod/CrystalDomeLightingFix.archive.xl",
    "r6/scripts/CrystalDomeLightingFix/CrystalDomeLightingFix.reds",
    "r6/scripts/CrystalDomeLightingFix/StandInNames.reds",
]
TEST_FILES = [
    "bin/x64/plugins/cyber_engine_tweaks/mods/CrystalDomeLightingFixTest/init.lua",
    "bin/x64/plugins/cyber_engine_tweaks/mods/CrystalDomeLightingFixTest/names.lua",
]


def main():
    files = FILES + (TEST_FILES if "--test" in sys.argv else [])
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", "CrystalDomeLightingFix.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(ROOT, f), f)
    print(out)
    for f in files:
        print("  ", f)


if __name__ == "__main__":
    main()
