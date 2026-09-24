from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"

GROUPS = {
    "CUTOFF": sorted((BASE).glob("run_*Ry/*.in")),
    "KPOINTS": sorted((BASE).glob("run_kpoints_*/*.in")),
    "SMEARING": sorted((BASE / "smearing_tests").glob("degauss_*/*.in")),
}


def read(path: Path) -> str:
    return path.read_text(errors="replace")


def extract(text: str, pattern: str):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def summarize(path: Path):
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


def inspect_group(name, paths):
    print()
    print("=" * 78)
    print(name)
    print("=" * 78)

    if not paths:
        raise SystemExit(f"[FAIL] Aucun input détecté pour {name}")

    for path in paths:
        p = summarize(path)

        print()
        print(path.relative_to(ROOT))

        for key, value in p.items():
            print(f"  {key:10s} = {value}")

    return [(path, summarize(path)) for path in paths]


print("=" * 78)
print("PHASE 78.9 — AUDIT READ-ONLY DE COHERENCE DES INPUTS QE")
print("=" * 78)
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier QE modifié")
print("[INFO] Aucun calcul scientifique lancé")

data = {
    name: inspect_group(name, paths)
    for name, paths in GROUPS.items()
}

print()
print("=" * 78)
print("CONTROLE DES PARAMETRES INVARIANTS")
print("=" * 78)

invariants = [
    "ecutrho",
    "nspin",
    "nat",
    "ntyp",
    "smearing",
    "conv_thr",
]

for group, records in data.items():
    print()
    print(f"--- {group} ---")

    for key in invariants:
        values = {item[1][key] for item in records}

        if len(values) == 1:
            print(f"[OK] {key:10s} constant = {next(iter(values))}")
        else:
            print(f"[WARN] {key:10s} varie : {sorted(values)}")

print()
print("=" * 78)
print("PARAMETRES TESTES")
print("=" * 78)

for group, records in data.items():
    print()
    print(f"--- {group} ---")

    for path, p in records:
        if group == "CUTOFF":
            print(
                f"{path.name}: "
                f"ecutwfc={p['ecutwfc']}, "
                f"degauss={p['degauss']}"
            )

        elif group == "KPOINTS":
            text = read(path)
            match = re.search(
                r"K_POINTS\s+\S+\s*\n\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)",
                text,
                re.IGNORECASE,
            )
            mesh = (
                f"{match.group(1)}x{match.group(2)}x{match.group(3)}"
                if match
                else "NON_DETECTE"
            )
            print(
                f"{path.name}: "
                f"kpoints={mesh}, "
                f"ecutwfc={p['ecutwfc']}"
            )

        elif group == "SMEARING":
            print(
                f"{path.name}: "
                f"degauss={p['degauss']}, "
                f"ecutwfc={p['ecutwfc']}"
            )

print()
print("=" * 78)
print("CONCLUSION PHASE 78.9")
print("=" * 78)
print("[OK] Audit des inputs terminé")
print("[OK] Aucun calcul exécuté")
print("[OK] Aucun fichier modifié")
print("[INFO] Toute anomalie éventuelle doit être examinée avant une nouvelle campagne QE")
