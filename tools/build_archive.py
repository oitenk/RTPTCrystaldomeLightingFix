"""Build CrystalDomeLightingFix.archive.

Makes an opaque stand-in for each dark Crystal Dome panel (same shape as the panel,
plain dark material, a few millimetres further out) and an ArchiveXL .app patch that
adds them to the car. The script reads the game's own files with the WolvenKit CLI,
so no CDPR files are kept in this repo.

usage: python -I tools/build_archive.py
"""
import copy
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOLVENKIT = r"D:\WolvenKit.Console-9.1.0\WolvenKit.CLI.exe"
GAME = r"C:\Games\steamapps\common\Cyberpunk 2077"
WORK = os.path.join(ROOT, "_archive", "build")        # git-ignored scratch space
OUT_DIR = os.path.join(ROOT, "archive", "pc", "mod")
ARCHIVE_NAME = "CrystalDomeLightingFix"
MOD_PATH = "crystal_dome_lighting_fix"

# How far outside the dome panel the stand-in sits, in metres. Enough to never
# flicker against the panel, small enough not to be seen.
OFFSET = 0.005

# Stand-in colour and roughness (metal_base). Dark and matte, like the panel when the dome is off.
BASE_COLOR = 0.03
ROUGHNESS = 1.0

CARS = [
    {
        "key": "hellhound",
        # The player's Hellhound is Phantom Liberty's (ep1), appearance player_01.
        "app": r"ep1\vehicles\appearances\standard\militech_hellhound__basic.app",
        "appearances": ["player_01"],
        "mesh_dir": r"base\vehicles\standard\v_standard3_militech_hellhound\entities\meshes",
        "mesh_prefix": "v_standard3_militech_hellhound__ext01_crystaldome_",
        # panel position -> component of the dark panel (the stand-in uses the same parent)
        "panels": {"f": "crystaldome_f_a", "fl": "crystaldome_fl_a", "fr": "crystaldome_fr_a",
                   "bl": "crystaldome_bl_a", "br": "crystaldome_br_a"},
    },
]


def run(*args):
    r = subprocess.run([WOLVENKIT, *args, "-v", "Minimal"], capture_output=True, text=True)
    errors = [l for l in r.stdout.splitlines() if "Error" in l and "Failed to export materials" not in l]
    if r.returncode != 0 or errors:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(f"WolvenKit failed: {' '.join(args[:2])}")


def path_regex(paths):
    """WolvenKit -r pattern matching exactly these depot paths."""
    return "^(" + "|".join(re.escape(p) for p in paths) + ")$"


def extract(paths, dest):
    """Unbundle game files (by exact depot path) and convert each one to JSON.

    Each file is converted on its own: the output is flat, and base game and
    Phantom Liberty copies of a file share a name."""
    raw = os.path.join(dest, "raw")
    out = os.path.join(dest, "json")
    os.makedirs(out, exist_ok=True)
    rx = path_regex(paths)
    run("unbundle", os.path.join(GAME, "archive", "pc", "content"), os.path.join(GAME, "archive", "pc", "ep1"),
        "-o", raw, "-r", rx)
    for p in paths:
        src = os.path.join(raw, p)
        if not os.path.exists(src):
            sys.exit(f"not extracted: {p}")
        run("convert", "serialize", src, "-o", out)
    return out


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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


def standin_component(template, name, mesh_path, offset, cruid, handle_id):
    c = copy.deepcopy(template)
    c["name"] = cname(name)
    c["id"] = str(cruid)
    c["mesh"] = depot(mesh_path)
    c["meshAppearance"] = cname("default")
    for k in ("castShadows", "castLocalShadows", "castRayTracedGlobalShadows"):
        c[k] = "Always"
    c["isEnabled"] = 1
    c["localTransform"]["Position"] = {"$type": "WorldPosition", "x": fixed(offset[0]), "y": fixed(offset[1]), "z": fixed(offset[2])}
    pt = c["parentTransform"]
    if "Data" not in pt:
        sys.exit(f"{name}: template parentTransform has no Data")
    pt["HandleId"] = str(handle_id)
    return c


def main():
    random.seed(20261106)
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    pack_root = os.path.join(WORK, "pack", ARCHIVE_NAME)
    src_json = os.path.join(WORK, "src_json")
    os.makedirs(src_json)
    os.makedirs(pack_root)

    for car in CARS:
        meshes = {pos: car["mesh_dir"] + "\\" + car["mesh_prefix"] + pos + "_a_01.mesh" for pos in car["panels"]}
        jdir = extract([car["app"], *meshes.values()], os.path.join(WORK, "game", car["key"]))
        glb_dir = os.path.join(WORK, "game", car["key"], "glb")
        os.makedirs(glb_dir, exist_ok=True)
        run("uncook", os.path.join(GAME, "archive", "pc", "content"), "-o", glb_dir,
            "-r", path_regex(meshes.values()),
            "--mesh-export-type", "MeshOnly", "--mesh-export-lod-filter")

        app = load(os.path.join(jdir, os.path.basename(car["app"]) + ".json"))
        defs = {a["Data"]["name"]["$value"]: a["Data"] for a in app["Data"]["RootChunk"]["appearances"]}

        handle = 5000
        new_defs = []
        cruids = {}
        for appearance in car["appearances"]:
            src_def = defs[appearance]
            chunks = src_def["compiledData"]["Data"]["Chunks"]
            by_name = {c["name"]["$value"]: c for c in chunks if "name" in c}
            comps = []
            for pos, panel in car["panels"].items():
                name = f"cdlf_standin_{pos}"
                mesh_path = f"{MOD_PATH}\\{car['key']}\\{name}.mesh"
                n = glb_mean_normal(os.path.join(glb_dir, os.path.splitext(meshes[pos])[0] + ".glb"))
                offset = tuple(-x * OFFSET for x in n)          # away from the cabin
                cruid = cruids.setdefault(name, random.getrandbits(63))
                handle += 1
                comps.append(standin_component(by_name[panel], name, mesh_path, offset, cruid, handle))
            d = copy.deepcopy(src_def)
            d["components"] = copy.deepcopy(comps)
            for c in d["components"]:                       # handle ids must be unique in the file
                handle += 1
                c["parentTransform"]["HandleId"] = str(handle)
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

        patch = copy.deepcopy(app)
        root = patch["Data"]["RootChunk"]
        root["appearances"] = [{"HandleId": str(9000 + i), "Data": d} for i, d in enumerate(new_defs)]
        root["censorshipMapping"] = []
        patch_name = f"{car['key']}_standins.app"
        out = os.path.join(src_json, MOD_PATH, car["key"])
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, patch_name + ".json"), "w", encoding="utf-8") as f:
            json.dump(patch, f, indent=2)
        for pos in car["panels"]:
            m = standin_mesh(load(os.path.join(jdir, os.path.basename(meshes[pos]) + ".json")))
            with open(os.path.join(out, f"cdlf_standin_{pos}.mesh.json"), "w", encoding="utf-8") as f:
                json.dump(m, f, indent=2)
        car["patch_path"] = f"{MOD_PATH}\\{car['key']}\\{patch_name}"

    # One file at a time: WolvenKit's output is flat, so each goes into its own depot folder.
    for dp, _, fs in os.walk(src_json):
        for f in fs:
            target = os.path.join(pack_root, os.path.relpath(dp, src_json))
            os.makedirs(target, exist_ok=True)
            run("convert", "deserialize", os.path.join(dp, f), "-o", target)
    built = [os.path.join(dp, f) for dp, _, fs in os.walk(pack_root) for f in fs]
    leftovers = [f for f in built if f.endswith(".json")]
    for f in leftovers:
        os.remove(f)
    print("built:", *[os.path.relpath(f, pack_root) for f in built if not f.endswith(".json")], sep="\n  ")
    run("pack", pack_root, "-o", OUT_DIR)

    with open(os.path.join(OUT_DIR, ARCHIVE_NAME + ".archive.xl"), "w", encoding="utf-8", newline="\n") as f:
        f.write("resource:\n  patch:\n")
        for car in CARS:
            f.write(f"    {car['patch_path']}:\n      - {car['app']}\n")
    print("done:", os.path.join(OUT_DIR, ARCHIVE_NAME + ".archive"))


def glb_mean_normal(path):
    """Average vertex normal of submesh 0, converted from glb axes (Y up) to game axes (Z up)."""
    import struct
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


if __name__ == "__main__":
    main()
