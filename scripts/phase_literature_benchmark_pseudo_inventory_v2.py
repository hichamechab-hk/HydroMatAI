#!/usr/bin/env python3

import re
from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

SEARCH_DIRS = [
    BASE,
    Path("/home/hk/HydroMatAI_MOF"),
    Path("/home/hk/software/qe-7.5"),
]

ELEMENTS = ["H", "K", "Rb", "Ge", "Sn", "Na", "Ca", "Sr", "Pd", "Ru"]

REPORT_DIR = BASE / "reports/literature_benchmarks"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT = REPORT_DIR / "literature_benchmark_pseudo_inventory_v2.txt"

print("=" * 78)
print("LITERATURE BENCHMARKS — PSEUDOPOTENTIAL INVENTORY V2")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier UPF modifié")
print("[INFO] Identification par contenu UPF + nom de fichier")
print()

upfs = set()

for root in SEARCH_DIRS:
    if not root.exists():
        continue

    try:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() == ".upf":
                upfs.add(p.resolve())
    except (PermissionError, OSError):
        pass

print(f"[INFO] UPF uniques trouvés : {len(upfs)}")
print()

records = []

for path in sorted(upfs):

    try:
        text = path.read_text(errors="ignore")
    except Exception:
        continue

    header = text[:100000]

    element = ""

    patterns = [
        r'\belement\s*=\s*"([A-Z][a-z]?)"',
        r"\belement\s*=\s*'([A-Z][a-z]?)'",
    ]

    for pattern in patterns:
        m = re.search(pattern, header, re.I)
        if m:
            element = m.group(1)
            break

    if element not in ELEMENTS:
        name = path.name

        for el in sorted(ELEMENTS, key=len, reverse=True):
            if re.search(
                rf"(^|[._-]){re.escape(el)}([._-]|$)",
                name,
                re.I,
            ):
                element = el
                break

    if element not in ELEMENTS:
        continue

    def get(patterns):
        for pattern in patterns:
            m = re.search(pattern, header, re.I)
            if m:
                return m.group(1).strip()
        return ""

    pseudo_type = get([
        r'\bpseudo_type\s*=\s*"([^"]+)"',
        r"\bpseudo_type\s*=\s*'([^']+)'",
    ])

    functional = get([
        r'\bfunctional\s*=\s*"([^"]+)"',
        r"\bfunctional\s*=\s*'([^']+)'",
    ])

    zval = get([
        r'\bz_valence\s*=\s*"([^"]+)"',
        r"\bz_valence\s*=\s*'([^']+)'",
    ])

    records.append({
        "element": element,
        "path": str(path),
        "filename": path.name,
        "pseudo_type": pseudo_type,
        "functional": functional,
        "zval": zval,
    })


def classify_functional(functional):
    f = functional.upper()

    if "PBE" in f:
        return "PBE"

    if "PBX" in f and "PW" in f:
        return "PBE_LIKE"

    if "PZ" in f:
        return "LDA"

    if "BLYP" in f:
        return "BLYP"

    return "UNKNOWN"


for element in ELEMENTS:

    matches = [
        r for r in records
        if r["element"] == element
    ]

    print("-" * 78)
    print(element)
    print("-" * 78)

    if not matches:
        print("STATUS : MISSING")
        print()
        continue

    print(f"STATUS : FOUND ({len(matches)})")

    for r in matches:
        family = classify_functional(r["functional"])

        print(f"FILE       : {r['filename']}")
        print(f"PATH       : {r['path']}")
        print(f"TYPE       : {r['pseudo_type'] or 'UNKNOWN'}")
        print(f"FUNCTIONAL : {r['functional'] or 'UNKNOWN'}")
        print(f"CLASS      : {family}")
        print(f"ZVAL       : {r['zval'] or 'UNKNOWN'}")
        print()


with REPORT.open("w", encoding="utf-8") as f:

    f.write("=" * 78 + "\n")
    f.write("LITERATURE BENCHMARKS — PSEUDOPOTENTIAL INVENTORY V2\n")
    f.write("=" * 78 + "\n")
    f.write("MODE = READ-ONLY\n\n")

    for element in ELEMENTS:

        matches = [
            r for r in records
            if r["element"] == element
        ]

        f.write(f"\n[{element}]\n")

        if not matches:
            f.write("STATUS = MISSING\n")
            continue

        f.write(f"STATUS = FOUND ({len(matches)})\n")

        for r in matches:
            f.write(f"FILE = {r['filename']}\n")
            f.write(f"PATH = {r['path']}\n")
            f.write(f"TYPE = {r['pseudo_type']}\n")
            f.write(f"FUNCTIONAL = {r['functional']}\n")
            f.write(f"ZVAL = {r['zval']}\n")


print("=" * 78)
print("SUMMARY")
print("=" * 78)

for element in ELEMENTS:

    matches = [
        r for r in records
        if r["element"] == element
    ]

    print(
        f"{element:4s} : "
        + (f"FOUND ({len(matches)})" if matches else "MISSING")
    )

print()
print(f"[REPORT] {REPORT}")
print()
print("[NEXT]")
print("Les pseudopotentiels seront sélectionnés seulement après")
print("identification d'un ensemble PBE cohérent et traçable.")
