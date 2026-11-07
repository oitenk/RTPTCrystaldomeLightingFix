"""Check the built archive: every patch's stand-ins point at meshes in the archive,
the component list matches the compiled data, and each sits on its panel's parent.

usage: python -I tools/verify_archive.py
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOLVENKIT = r"D:\WolvenKit.Console-9.1.0\WolvenKit.CLI.exe"
ARCHIVE = os.path.join(ROOT, "archive", "pc", "mod", "CrystalDomeLightingFix.archive")
XL = ARCHIVE + ".xl"
WORK = os.path.join(ROOT, "_archive", "verify")


def fnv1a64(s):
    """Resource path hash used by the game (FNV-1a 64 of the lower-case path)."""
    h = 0xcbf29ce484222325
    for b in s.lower().encode("utf-8"):
        h = ((h ^ b) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def wk(*args):
    r = subprocess.run([WOLVENKIT, *args, "-v", "Minimal"], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-2000:])
    return r.stdout


def val(v):
    if isinstance(v, dict):
        if "$value" in v:
            return v["$value"]
        if "DepotPath" in v:
            return val(v["DepotPath"])
    return v


def main():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    raw = os.path.join(WORK, "raw")
    wk("unbundle", ARCHIVE, "-o", raw)
    files = [os.path.relpath(os.path.join(dp, f), raw) for dp, _, fs in os.walk(raw) for f in fs]
    hashes = {str(fnv1a64(f)): f for f in files} | {f: f for f in files}

    patched = []
    for line in open(XL, encoding="utf-8"):
        s = line.strip()
        if s.endswith(".app:"):
            patched.append(s[:-1])
    problems = 0
    total = 0
    for p in patched:
        if p not in files:
            print("MISSING patch file:", p)
            problems += 1
            continue
        out = os.path.join(WORK, "json", os.path.dirname(p))
        os.makedirs(out, exist_ok=True)
        wk("convert", "serialize", os.path.join(raw, p), "-o", out)
        d = json.load(open(os.path.join(out, os.path.basename(p) + ".json"), encoding="utf-8"))
        for a in d["Data"]["RootChunk"]["appearances"]:
            ad = a["Data"]
            listed = [val(c["name"]) for c in ad["components"]]
            chunks = ad["compiledData"]["Data"]["Chunks"]
            if listed != [val(c["name"]) for c in chunks]:
                print(f"{p} {val(ad['name'])}: component list and compiled data differ")
                problems += 1
            for c in chunks:
                total += 1
                mesh = str(val(c["mesh"]))
                parent = val(c["parentTransform"]["Data"]["bindName"])
                if mesh not in hashes:
                    print(f"{p} {val(ad['name'])} {val(c['name'])}: mesh {mesh} not in archive")
                    problems += 1
                if not val(c["name"]).startswith("cdlf_") or not parent:
                    print(f"{p} {val(ad['name'])} {val(c['name'])}: bad name or parent {parent}")
                    problems += 1
    meshes = [f for f in files if f.endswith(".mesh")]
    print(f"{len(patched)} patches, {total} stand-in components, {len(meshes)} meshes, problems: {problems}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
