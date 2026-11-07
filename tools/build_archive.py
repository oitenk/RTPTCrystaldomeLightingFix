"""Build CrystalDomeLightingFix.archive and the generated name lists.

For every dark Crystal Dome panel on every dome vehicle found by survey_dome_cars.py,
make an opaque stand-in (same shape as the panel, plain dark material, a few
millimetres further out) and an ArchiveXL .app patch per appearance file that adds
the stand-ins next to their panels. The script reads the game's own files with the
WolvenKit CLI, so no CDPR files are kept in this repo.

Also writes the list of stand-in component names for the script and the test hotkey.

usage: python -I tools/survey_dome_cars.py   (once, or after a game patch)
       python -I tools/build_archive.py
"""
import copy
import json
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOLVENKIT = r"D:\WolvenKit.Console-9.1.0\WolvenKit.CLI.exe"
GAME = r"C:\Games\steamapps\common\Cyberpunk 2077"
SOURCES = [os.path.join(GAME, "archive", "pc", "content"), os.path.join(GAME, "archive", "pc", "ep1")]
SURVEY = os.path.join(ROOT, "_archive", "survey", "dome_cars.json")
WORK = os.path.join(ROOT, "_archive", "build")        # git-ignored scratch space
OUT_DIR = os.path.join(ROOT, "archive", "pc", "mod")
ARCHIVE_NAME = "CrystalDomeLightingFix"
MOD_PATH = "crystal_dome_lighting_fix"
NAMES_REDS = os.path.join(ROOT, "r6", "scripts", "CrystalDomeLightingFix", "StandInNames.reds")
NAMES_LUA = os.path.join(ROOT, "bin", "x64", "plugins", "cyber_engine_tweaks", "mods", "CrystalDomeLightingFixTest", "names.lua")

# Stand-in component names: this prefix + the dark panel's own component name.
PREFIX = "cdlf_"

# How far outside the dome panel the stand-in sits, in metres. Enough to never
# flicker against the panel, small enough not to be seen.
OFFSET = 0.005

# Stand-in colour and roughness (metal_base). Dark and matte, like the panel when the dome is off.
BASE_COLOR = 0.03
ROUGHNESS = 1.0

# Flying vehicles are left out for now (only reachable through other mods).
SKIP_APPS = {
    r"base\vehicles\appearances\special\militech_manticore__basic.app",
    r"ep1\vehicles\appearances\special\militech_manticore_trauma_team.app",
    r"base\vehicles\appearances\special\rayfield_excalibur__basic.app",
    r"ep1\vehicles\appearances\special\av_rayfield_excalibur_nusa_basic.app",
    r"base\vehicles\appearances\special\militech_basilisk__basic.app",
}
# Holograms are see-through by design; an opaque panel would show on them.
SKIP_APPEARANCE = re.compile(r"holog", re.I)


def run(*args):
    r = subprocess.run([WOLVENKIT, *args, "-v", "Minimal"], capture_output=True, text=True)
    errors = [l for l in r.stdout.splitlines() if "Error" in l and "Failed to export materials" not in l]
    if r.returncode != 0 or errors:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(f"WolvenKit failed: {' '.join(args[:2])}")


def path_regex(paths):
    """WolvenKit -r pattern matching exactly these depot paths."""
    return "^(" + "|".join(re.escape(p) for p in paths) + ")$"


def in_batches(items, n=40):
    items = sorted(items)
    for i in range(0, len(items), n):
        yield items[i:i + n]


def extract(paths, dest):
    """Unbundle game files (by exact depot path) and convert each one to JSON next to its depot path."""
    raw = os.path.join(dest, "raw")
    out = os.path.join(dest, "json")
    for batch in in_batches(paths):
        run("unbundle", *SOURCES, "-o", raw, "-r", path_regex(batch))
    for p in paths:
        src = os.path.join(raw, p)
        if not os.path.exists(src):
            sys.exit(f"not extracted: {p}")
        target = os.path.dirname(os.path.join(out, p))
        os.makedirs(target, exist_ok=True)
        run("convert", "serialize", src, "-o", target)
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def cname(v):
    return {"$type": "CName", "$storage": "string", "$value": v}


def depot(p):
    return {"DepotPath": {"$type": "ResourcePath", "$storage": "string", "$value": p}, "Flags": "Default"}


def standin_mesh(src):
    """Same geometry as the panel, every chunk on one plain dark metal_base material."""
    d = copy.deepcopy(src)
    r = d["Data"]["RootChunk"]
    name = "cdlf_standin"
    r["materialEntries"] = [{"$type": "CMeshMaterialEntry", "index": 0, "isLocalInstance": 1, "name": cname(name)}]
    r["externalMaterials"] = []
    r["preloadExternalMaterials"] = []
    r["localMaterialInstances"] = []
    r["localMaterialBuffer"] = {"$type": "meshMeshMaterialBuffer", "materials": [], "rawData": None, "rawDataHeaders": []}
    r["preloadLocalMaterialInstances"] = [{
        "HandleId": "1001",
        "Data": {
            "$type": "CMaterialInstance",
            "audioTag": cname("None"),
            "baseMaterial": depot(r"engine\materials\metal_base.remt"),
            "cookingPlatform": "PLATFORM_None",
            "enableMask": 0,
            "metadata": None,
            "resourceVersion": 4,
            "values": [
                {"$type": "Vector4", "BaseColorScale": {"$type": "Vector4", "W": 1, "X": BASE_COLOR, "Y": BASE_COLOR, "Z": BASE_COLOR}},
                {"$type": "Float", "RoughnessScale": ROUGHNESS},
            ],
        },
    }]
    for app in r["appearances"]:
        a = app["Data"]
        a["chunkMaterials"] = [cname(name) for _ in a["chunkMaterials"]]
    return d


def fixed(v):
    return {"$type": "FixedPoint", "Bits": int(round(v * 131072))}


def standin_component(template, name, mesh_path, offset, cruid):
    """Copy of the panel's component: same parent and placement, our mesh, pushed out by offset."""
    c = copy.deepcopy(template)
    c["name"] = cname(name)
    c["id"] = str(cruid)
    c["mesh"] = depot(mesh_path)
    c["meshAppearance"] = cname("default")
    for k in ("castShadows", "castLocalShadows", "castRayTracedGlobalShadows"):
        c[k] = "Always"
    c["isEnabled"] = 1
    pos = c["localTransform"]["Position"]
    base = [pos[k]["Bits"] / 131072 for k in "xyz"]
    c["localTransform"]["Position"] = {"$type": "WorldPosition", **{k: fixed(base[i] + offset[i]) for i, k in enumerate("xyz")}}
    pt = c.get("parentTransform")
    if not isinstance(pt, dict) or "Data" not in pt:
        sys.exit(f"{name}: panel parentTransform has no Data")
    return c


def glb_mean_normal(path):
    """Average vertex normal of submesh 0, converted from glb axes (Y up) to game axes (Z up)."""
    d = open(path, "rb").read()
    jl = struct.unpack_from("<I", d, 12)[0]
    js = json.loads(d[20:20 + jl])
    bo = 20 + jl
    b = d[bo + 8:bo + 8 + struct.unpack_from("<I", d, bo)[0]]
    p = js["meshes"][0]["primitives"][0]
    a = js["accessors"][p["attributes"]["NORMAL"]]
    bv = js["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    st = bv.get("byteStride", 12)
    s = [0.0, 0.0, 0.0]
    for k in range(a["count"]):
        n = struct.unpack_from("<fff", b, off + k * st)
        for i in range(3):
            s[i] += n[i]
    g = (s[0], -s[2], s[1])                      # glb (x, y up, z) -> game (x, y forward, z up)
    L = math.sqrt(sum(x * x for x in g))
    return tuple(x / L for x in g)


def targets_from_survey():
    """{app: {appearance: [dark panel rows]}} for the vehicles this mod covers."""
    if not os.path.exists(SURVEY):
        sys.exit("run tools/survey_dome_cars.py first")
    s = load(SURVEY)
    out = {}
    for car in s["cars"].values():
        for app, a in car["apps"].items():
            if app in SKIP_APPS:
                continue
            for appearance, panels in a["panels"].items():
                if SKIP_APPEARANCE.search(appearance):
                    continue
                dark = [p for p in panels if p["kind"] == "dark"]
                if dark:
                    out.setdefault(app, {})[appearance] = dark
    return out


def standin_path(panel_mesh):
    return f"{MOD_PATH}\\meshes\\{os.path.splitext(os.path.basename(panel_mesh))[0]}_cdlf.mesh"


def patch_path(app):
    top = app.split("\\")[0]
    return f"{MOD_PATH}\\patches\\{top}_{os.path.basename(app)}"


def write_name_lists(names):
    names = sorted(names)
    reds = ["// Generated by tools/build_archive.py; do not edit.",
            "// Stand-in components added by CrystalDomeLightingFix.archive, one per dark dome panel name.",
            "",
            "private func CDLF_StandInNames() -> array<CName> {",
            "    return ["]
    reds += [f'        n"{n}",' for n in names]
    reds[-1] = reds[-1].rstrip(",")
    reds += ["    ];", "}", ""]
    with open(NAMES_REDS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(reds))
    lua = ["-- Generated by tools/build_archive.py; do not edit.", "return {"] + [f'    "{n}",' for n in names] + ["}", ""]
    with open(NAMES_LUA, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lua))


def main():
    random.seed(20261106)
    targets = targets_from_survey()
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    pack_root = os.path.join(WORK, "pack", ARCHIVE_NAME)
    src_json = os.path.join(WORK, "src_json")
    game = os.path.join(WORK, "game")
    os.makedirs(src_json)
    os.makedirs(pack_root)

    panel_meshes = sorted({p["mesh"] for per in targets.values() for panels in per.values() for p in panels})
    by_base = {}
    for m in panel_meshes:
        by_base.setdefault(standin_path(m), []).append(m)
    clashes = {k: v for k, v in by_base.items() if len(v) > 1}
    if clashes:
        sys.exit(f"stand-in mesh names clash: {clashes}")

    jdir = extract(sorted(targets) + panel_meshes, game)
    glb_dir = os.path.join(game, "glb")
    for batch in in_batches(panel_meshes):
        run("uncook", *SOURCES, "-o", glb_dir, "-r", path_regex(batch),
            "--mesh-export-type", "MeshOnly", "--mesh-export-lod-filter")

    # Stand-in meshes, and how far to push each one out (away from the cabin, against its normal).
    offsets = {}
    for m in panel_meshes:
        save(standin_mesh(load(os.path.join(jdir, m) + ".json")), os.path.join(src_json, standin_path(m)) + ".json")
        n = glb_mean_normal(os.path.join(glb_dir, os.path.splitext(m)[0] + ".glb"))
        offsets[m] = tuple(-x * OFFSET for x in n)

    names = set()
    summary = []
    for app, per in sorted(targets.items()):
        src = load(os.path.join(jdir, app) + ".json")
        defs = {a["Data"]["name"]["$value"]: a["Data"] for a in src["Data"]["RootChunk"]["appearances"]}
        cruids = {}
        handle = 5000
        new_defs = []
        for appearance, panels in sorted(per.items()):
            src_def = defs[appearance]
            by_name = {c["name"]["$value"]: c for c in src_def["compiledData"]["Data"]["Chunks"] if "name" in c}
            comps = []
            for p in panels:
                name = PREFIX + p["name"]
                cruid = cruids.setdefault(name, random.getrandbits(63))
                comps.append(standin_component(by_name[p["name"]], name, standin_path(p["mesh"]), offsets[p["mesh"]], cruid))
                names.add(name)
            # Handle ids must be unique in the file: number the component list and the compiled copy apart.
            for c in comps:
                handle += 1
                c["parentTransform"]["HandleId"] = str(handle)
            listed = copy.deepcopy(comps)
            for c in listed:
                handle += 1
                c["parentTransform"]["HandleId"] = str(handle)
            d = copy.deepcopy(src_def)
            d["components"] = listed
            d["compiledData"]["Data"]["Chunks"] = comps
            d["compiledData"]["Data"]["CruidDict"] = {str(i): c["id"] for i, c in enumerate(comps)}
            d["compiledData"]["Data"]["CruidIndex"] = -1
            for k in ("partsValues", "partsOverrides", "partsMasks", "resolvedDependencies", "looseDependencies",
                      "hitRepresentationOverrides"):
                d[k] = []
            d["visualTags"] = {"$type": "redTagList", "tags": []}
            d["inheritedVisualTags"] = {"$type": "redTagList", "tags": []}
            d["proxyMesh"] = {"DepotPath": {"$type": "ResourcePath", "$storage": "uint64", "$value": "0"}, "Flags": "Soft"}
            d["proxyMeshAppearance"] = cname("None")
            new_defs.append(d)
        patch = copy.deepcopy(src)
        root = patch["Data"]["RootChunk"]
        root["appearances"] = [{"HandleId": str(9000 + i), "Data": d} for i, d in enumerate(new_defs)]
        root["censorshipMapping"] = []
        save(patch, os.path.join(src_json, patch_path(app)) + ".json")
        summary.append((app, len(per), sorted({p["name"] for ps in per.values() for p in ps})))

    # One file at a time: WolvenKit's output is flat, so each goes into its own depot folder.
    for dp, _, fs in os.walk(src_json):
        for f in fs:
            target = os.path.join(pack_root, os.path.relpath(dp, src_json))
            os.makedirs(target, exist_ok=True)
            run("convert", "deserialize", os.path.join(dp, f), "-o", target)
    built = [os.path.join(dp, f) for dp, _, fs in os.walk(pack_root) for f in fs]
    for f in built:
        if f.endswith(".json"):
            os.remove(f)
    built = [f for f in built if not f.endswith(".json")]
    expected = len(panel_meshes) + len(targets)
    if len(built) != expected:
        sys.exit(f"built {len(built)} files, expected {expected}")
    run("pack", pack_root, "-o", OUT_DIR)

    with open(os.path.join(OUT_DIR, ARCHIVE_NAME + ".archive.xl"), "w", encoding="utf-8", newline="\n") as f:
        f.write("resource:\n  patch:\n")
        for app in sorted(targets):
            f.write(f"    {patch_path(app)}:\n      - {app}\n")
    write_name_lists(names)

    for app, n, panels in summary:
        print(f"{app}: {n} appearances, panels {', '.join(panels)}")
    print(f"{len(panel_meshes)} stand-in meshes, {len(targets)} patches, {len(names)} component names")
    print("done:", os.path.join(OUT_DIR, ARCHIVE_NAME + ".archive"))


if __name__ == "__main__":
    main()
