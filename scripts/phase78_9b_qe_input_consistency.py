from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"


def read(path: Path) -> str:
    return path.read_text(errors="replace")


def extract(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def params(path: Path):
    text = read(path)

    return {
        "ecutwfc": extract(text, r"ecutwfc\s*=\s*([0-9.]+)"),
        "ecutrho": extract(text, r"ecutrho\s*=\s*([0-9.]+)"),
        "nspin": extract(text, r"nspin\s*=\s*([0-9]+)"),
        "degauss": extract(text, r"degauss\s*=\s*([0-9.]+)"),
        "smearing": extract(text, r"smearing\s*=\s*['\"]([^'\"]+)"),
        "nat": extract(text, r"nat\s*=\s*([0-9]+)"),
        "ntyp": extract(text, r"ntyp\s*=\s*([0-9]+)"),
        "conv_thr": extract(text, r"conv_thr\s*=\s*([0-9.eE+-]+)"),
    }


def kmesh(path: Path):
    text = read(path)

    m = re.search(
        r"K_POINTS\s+\S+\s*\n\s*"
        r"([0-9]+)\s+([0-9]+)\s+([0-9]+)",
        text,
        re.IGNORECASE,
    )

    if not m:
        return None

    return f"{m.group(1)}x{m.group(2)}x{m.group(3)}"


cutoff = sorted(BASE.glob("cutoff_*_2x2x2.in"))
kpoints = sorted(BASE.glob("kpoints_*_60Ry.in"))
smearing = sorted(
    (BASE / "smearing_tests").glob("degauss_*/*.in")
)

groups = {
    "CUTOFF": cutoff,
    "KPOINTS": kpoints,
    "SMEARING": smearing,
}

print("=" * 78)
print("PHASE 78.9B — AUDIT READ-ONLY DE COHERENCE DES INPUTS QE")
print("=" * 78)
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier QE modifié")
print("[INFO] Aucun calcul scientifique lancé")

for name, paths in groups.items():

    print()
    print("=" * 78)
    print(name)
    print("=" * 78)

    if not paths:
        raise SystemExit(f"[FAIL] Aucun input principal pour {name}")

    print(f"[OK] {len(paths)} inputs principaux détectés")

    for path in paths:
        p = params(path)

        print()
        print(path.relative_to(ROOT))

        print(f"  ecutwfc  = {p['ecutwfc']}")
        print(f"  ecutrho  = {p['ecutrho']}")
        print(f"  nspin    = {p['nspin']}")
        print(f"  smearing = {p['smearing']}")
        print(f"  degauss  = {p['degauss']}")
        print(f"  nat      = {p['nat']}")
        print(f"  ntyp     = {p['ntyp']}")
        print(f"  conv_thr = {p['conv_thr']}")

        if name == "KPOINTS":
            print(f"  kmesh    = {kmesh(path)}")

print()
print("=" * 78)
print("CONTROLE DES PARAMETRES INVARIANTS")
print("=" * 78)

# Paramètres qui doivent rester identiques dans chaque série.
invariants = [
    "ecutrho",
    "nspin",
    "nat",
    "ntyp",
    "smearing",
    "conv_thr",
]

for name, paths in groups.items():

    records = [params(path) for path in paths]

    print()
    print(f"--- {name} ---")

    for key in invariants:
        values = {record[key] for record in records}

        if len(values) == 1:
            print(f"[OK]   {key:10s} constant = {next(iter(values))}")
        else:
            print(f"[WARN] {key:10s} varie = {sorted(values)}")

print()
print("=" * 78)
print("CONTROLE DES PARAMETRES VARIABLES")
print("=" * 78)

cutoff_values = {
    p["ecutwfc"]
    for p in map(params, cutoff)
}

kpoint_values = {
    kmesh(path)
    for path in kpoints
}

smearing_values = {
    p["degauss"]
    for p in map(params, smearing)
}

print(f"CUTOFF ecutwfc : {sorted(cutoff_values)}")
print(f"K-POINTS        : {sorted(kpoint_values)}")
print(f"SMEARING        : {sorted(smearing_values)}")

assert len(cutoff_values) == 3
assert len(kpoint_values) == 3
assert len(smearing_values) == 4

print("[OK] Paramètres variables correctement identifiés")

print()
print("=" * 78)
print("EXCLUSION DES INPUTS AUXILIAIRES")
print("=" * 78)

auxiliary = list(
    BASE.glob("kpoints_smearing_0.002Ry/*/*.in")
)

print(f"Inputs auxiliaires détectés : {len(auxiliary)}")

for path in auxiliary:
    print(f"[INFO] Exclu : {path.relative_to(ROOT)}")

assert all(
    path not in cutoff
    and path not in kpoints
    and path not in smearing
    for path in auxiliary
)

print("[OK] Inputs auxiliaires exclus des trois séries principales")

print()
print("=" * 78)
print("CONCLUSION PHASE 78.9B")
print("=" * 78)
print("[OK] 3 inputs cutoff")
print("[OK] 3 inputs k-points")
print("[OK] 4 inputs smearing")
print("[OK] Inputs auxiliaires séparés")
print("[OK] Audit terminé sans exécution QE")
print("[OK] Aucun fichier modifié")
