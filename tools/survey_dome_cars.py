"""Find every vehicle with a Crystal Dome and the dark panels on it.

Reads the game's own files with the WolvenKit CLI (nothing from the game is kept):
1. every vehicle root entity (.ent) in the base game and Phantom Liberty,
2. those that carry the crystal_dome_* effects, and the .app files and appearances they use,
3. every mesh component in those appearances, and which of its meshes use the
   Crystal Dome materials (the dark one is base\\fx\\_shaders\\crystal_dome_opaque*.mt).

Writes _archive/survey/dome_cars.json and prints a summary.
usage: python -I tools/survey_dome_cars.py
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WOLVENKIT = r"D:\WolvenKit.Console-9.1.0\WolvenKit.CLI.exe"
GAME = r"C:\Games\steamapps\common\Cyberpunk 2077\archive\pc"
WORK = os.path.join(ROOT, "_archive", "survey")
SOURCES = {"base": os.path.join(GAME, "content"), "ep1": os.path.join(GAME, "ep1")}


def wk(*args):
    r = subprocess.run([WOLVENKIT, *args, "-v", "Minimal"], capture_output=True, text=True)
    return r.stdout


def unbundle(rx, dest):
    """Extract matching files from both game folders; base and ep1 keep their own top folders."""
    wk("unbundle", *SOURCES.values(), "-o", dest, "-r", rx)


def serialize_tree(raw, out):
    """Convert every file under raw to JSON at the same relative path (WolvenKit's own output is flat)."""
    for dp, _, fs in os.walk(raw):
        if not fs:
            continue
        target = os.path.join(out, os.path.relpath(dp, raw))
        os.makedirs(target, exist_ok=True)
        todo = [f for f in fs if not os.path.exists(os.path.join(target, f + ".json"))]
        if todo:
            wk("convert", "serialize", dp, "-o", target)


def val(v):
    if isinstance(v, dict):
        if "$value" in v:
            return v["$value"]
        if "DepotPath" in v:
            return val(v["DepotPath"])
    return v


def walk(o, fn):
    if isinstance(o, dict):
        fn(o)
        for v in o.values():
            walk(v, fn)
    elif isinstance(o, list):
        for v in o:
            walk(v, fn)


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def json_path(tree, depot_path):
    return os.path.join(tree, depot_path) + ".json"


def main():
    os.makedirs(WORK, exist_ok=True)
    raw, js = os.path.join(WORK, "raw"), os.path.join(WORK, "json")

    # 1. vehicle root entities (base\vehicles\<class>\x.ent, ep1\vehicles\<class>\x.ent)
    unbundle(r"^(base|ep1)\\vehicles\\[a-z0-9_]+\\[a-z0-9_]+\.ent$", raw)
    serialize_tree(raw, js)

    cars = {}
    for dp, _, fs in os.walk(js):
        for f in fs:
            if not f.endswith(".ent.json"):
                continue
            depot = os.path.relpath(os.path.join(dp, f), js)[:-5]
            d = load(os.path.join(dp, f))
            text = json.dumps(d)
            if "crystal_dome_start" not in text and "crystal_dome_instant_on" not in text:
                continue
            apps = {}
            def grab(o):
                if o.get("$type") == "entTemplateAppearance":
                    apps.setdefault(val(o.get("appearanceResource")), []).append(val(o.get("appearanceName")))
            walk(d, grab)
            cars[depot] = {"apps": apps}

    # 2. their appearance files
    app_paths = sorted({a for c in cars.values() for a in c["apps"] if a})
    unbundle("^(" + "|".join(re.escape(p) for p in app_paths) + ")$", raw)
    serialize_tree(raw, js)

    comps_by_app = {}
    mesh_paths = set()
    for app in app_paths:
        d = load(json_path(js, app))
        out = {}
        for a in d["Data"]["RootChunk"]["appearances"]:
            ad = a["Data"]
            rows = []
            for c in ad["compiledData"]["Data"]["Chunks"]:
                if "mesh" not in c or "name" not in c:
                    continue
                pt = c.get("parentTransform") or {}
                pd = pt.get("Data", {}) if isinstance(pt, dict) else {}
                rows.append({
                    "name": val(c["name"]), "type": c["$type"], "mesh": val(c["mesh"]),
                    "parent": val(pd.get("bindName")), "slot": val(pd.get("slotName")),
                    "castShadows": c.get("castShadows"), "meshAppearance": val(c.get("meshAppearance")),
                })
                mesh_paths.add(val(c["mesh"]))
            out[val(ad["name"])] = rows
        comps_by_app[app] = out

    # 3. meshes that could be dome panels or windows
    likely = sorted(p for p in mesh_paths if p and re.search(r"crystal|dome|window|canopy|glass", p, re.I))
    for i in range(0, len(likely), 40):
        unbundle("^(" + "|".join(re.escape(p) for p in likely[i:i + 40]) + ")$", raw)
    serialize_tree(raw, js)
    mesh_mats = {}
    for p in likely:
        jp = json_path(js, p)
        if not os.path.exists(jp):
            continue
        mats = set()
        def grab(o):
            if o.get("$type") == "CMaterialInstance" or "baseMaterial" in o:
                b = val(o.get("baseMaterial"))
                if isinstance(b, str):
                    mats.add(b)
            if o.get("$type") == "CMeshMaterialEntry":
                pass
        walk(load(jp), grab)
        mesh_mats[p] = sorted(mats)

    # 4. follow every external material (.mi) back to its shader (.mt / .remt): a car can have
    #    its own dome material built on a shared one (the Caliburn's fx_crystaldome_caliburn.mi).
    shader_of = {}
    pending = {m for ms in mesh_mats.values() for m in ms if m.endswith(".mi")}
    while pending:
        unbundle("^(" + "|".join(re.escape(p) for p in sorted(pending)) + ")$", raw)
        serialize_tree(raw, js)
        nxt = set()
        for m in pending:
            jp = json_path(js, m)
            base = None
            if os.path.exists(jp):
                root = load(jp)["Data"]["RootChunk"]
                base = val(root.get("baseMaterial"))
            shader_of[m] = base
            if isinstance(base, str) and base.endswith(".mi") and base not in shader_of:
                nxt.add(base)
        pending = nxt

    def final_shader(m):
        seen = set()
        while isinstance(m, str) and m.endswith(".mi") and m not in seen:
            seen.add(m)
            m = shader_of.get(m)
        return m or ""

    mesh_shaders = {p: sorted({final_shader(m) for m in ms}) for p, ms in mesh_mats.items()}

    def dome_kind(mesh):
        shaders = " ".join(mesh_shaders.get(mesh, []))
        if "crystal_dome_opaque_backface" in shaders:
            return "dark-backface"
        if "crystal_dome_opaque" in shaders:
            return "dark"
        if "crystal_dome.mt" in shaders:
            return "clear"
        return None

    result = {}
    for ent, c in sorted(cars.items()):
        car = {"apps": {}}
        for app, names in c["apps"].items():
            if not app:
                continue
            per = {}
            for appearance, rows in comps_by_app.get(app, {}).items():
                panels = [dict(r, kind=dome_kind(r["mesh"])) for r in rows if dome_kind(r["mesh"])]
                if panels:
                    per[appearance] = panels
            car["apps"][app] = {"entity_appearances": sorted(set(names)), "panels": per}
        result[ent] = car
    with open(os.path.join(WORK, "dome_cars.json"), "w", encoding="utf-8") as f:
        json.dump({"cars": result, "mesh_materials": mesh_mats, "mesh_shaders": mesh_shaders}, f, indent=1)

    for ent, car in result.items():
        print(ent)
        for app, a in car["apps"].items():
            print("   ", app, "| appearances in entity:", len(a["entity_appearances"]))
            for appearance, panels in a["panels"].items():
                dark = [p["name"] for p in panels if p["kind"].startswith("dark")]
                print(f"      {appearance:28s} dark: {', '.join(dark) or '-'}")


if __name__ == "__main__":
    main()
