#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

SEARCH_DIRS = [
    BASE / "data/literature_benchmarks",
    BASE / "calculations",
    BASE / "pseudo",
    BASE / "pseudopotentials",
    Path("/home/hk/HydroMatAI_MOF"),
    Path("/home/hk/software/qe-7.5"),
]

ELEMENTS = [
    "H", "K", "Rb", "Ge", "Sn",
    "Na", "Ca", "Sr", "Pd", "Ru",
]

REPORT_DIR = BASE / "reports/literature_benchmarks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = REPORT_DIR / "literature_benchmark_pseudo_audit.txt"

print("=" * 78)
print("LITERATURE BENCHMARKS — PSEUDOPOTENTIAL AUDIT")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier UPF modifié")
print("[INFO] Recherche des pseudopotentiels réellement disponibles")
print()

files = {}

for directory in SEARCH_DIRS:
    if not directory.exists():
        continue

    try:
        for p in directory.rglob("*.UPF"):
            files[p.resolve()] = p.resolve()
    except PermissionError:
        pass

    try:
        for p in directory.rglob("*.upf"):
            files[p.resolve()] = p.resolve()
    except PermissionError:
        pass

files = sorted(files.values())

print(f"[INFO] UPF trouvés : {len(files)}")
print()

def detect_element(path):
    name = path.name

    for element in sorted(ELEMENTS, key=len, reverse=True):
        if re.search(
            rf"(^|[._-]){re.escape(element)}([._-]|$)",
            name,
            re.I,
        ):
            return element

    text = path.read_text(errors="ignore")[:50000]

    m = re.search(
        r'element\s*=\s*["\']([A-Z][a-z]?)["\']',
        text,
        re.I,
    )

    if m:
        return m.group(1)

    return "UNKNOWN"


def read_attributes(path):
    text = path.read_text(errors="ignore")[:100000]

    def get(attr):
        patterns = [
            rf'{attr}\s*=\s*"([^"]+)"',
            rf"{attr}\s*=\s*'([^']+)'",
        ]

        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(1)

        return ""

    return {
        "element": get("element"),
        "pseudo_type": get("pseudo_type"),
        "functional": get("functional"),
        "z_valence": get("z_valence"),
        "generated": get("generated"),
    }


rows = []

for p in files:
    element = detect_element(p)
    attrs = read_attributes(p)

    if element not in ELEMENTS:
        continue

    rows.append({
        "element": element,
        "file": str(p),
        "pseudo_type": attrs["pseudo_type"],
        "functional": attrs["functional"],
        "z_valence": attrs["z_valence"],
        "generated": attrs["generated"],
    })


for element in ELEMENTS:
    matches = [r for r in rows if r["element"] == element]

    print("-" * 78)
    print(f"{element}")
    print("-" * 78)

    if not matches:
        print("[MISSING] Aucun pseudopotentiel trouvé")
        print()
        continue

    for r in matches:
        print(f"FILE       : {r['file']}")
        print(f"TYPE       : {r['pseudo_type'] or 'UNKNOWN'}")
        print(f"FUNCTIONAL : {r['functional'] or 'UNKNOWN'}")
        print(f"ZVAL       : {r['z_valence'] or 'UNKNOWN'}")
        print(f"GENERATED   : {r['generated'] or 'UNKNOWN'}")
        print()


with REPORT.open("w", encoding="utf-8") as f:
    f.write("=" * 78 + "\n")
    f.write("LITERATURE BENCHMARKS — PSEUDOPOTENTIAL AUDIT\n")
    f.write("=" * 78 + "\n")
    f.write("MODE = READ-ONLY\n")
    f.write("No pw.x / No UPF modification\n\n")

    for element in ELEMENTS:
        f.write(f"\n[{element}]\n")

        matches = [r for r in rows if r["element"] == element]

        if not matches:
            f.write("STATUS = MISSING\n")
            continue

        f.write(f"STATUS = FOUND ({len(matches)})\n")

        for r in matches:
            f.write(f"FILE = {r['file']}\n")
            f.write(f"TYPE = {r['pseudo_type']}\n")
            f.write(f"FUNCTIONAL = {r['functional']}\n")
            f.write(f"ZVAL = {r['z_valence']}\n")
            f.write(f"GENERATED = {r['generated']}\n")


print("=" * 78)
print("SUMMARY")
print("=" * 78)

for element in ELEMENTS:
    n = sum(r["element"] == element for r in rows)

    if n:
        print(f"{element:4s} : FOUND ({n})")
    else:
        print(f"{element:4s} : MISSING")

print()
print(f"[REPORT] {REPORT}")
print()
print("[IMPORTANT]")
print("Ne pas lancer pw.x avant validation de cet inventaire.")
print("Les pseudopotentiels doivent être homogènes autant que possible")
print("pour permettre une comparaison DFT interprétable.")
