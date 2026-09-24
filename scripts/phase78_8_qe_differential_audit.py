from __future__ import annotations

from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"


def energy(path: Path) -> float:
    text = path.read_text(errors="replace")
    values = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
    )
    if not values:
        raise RuntimeError(f"Energie absente : {path}")
    return float(values[-1])


def analyze(name, records):
    print()
    print(f"===== {name} =====")

    values = [(label, energy(path)) for label, path in records]

    for label, value in values:
        print(f"{label:12s} : {value:.8f} Ry")

    print()
    print("DIFFERENCES CONSECUTIVES")

    deltas = []

    for (label_a, e_a), (label_b, e_b) in zip(values, values[1:]):
        delta = e_b - e_a
        abs_delta = abs(delta)
        deltas.append(abs_delta)

        print(
            f"{label_a:12s} -> {label_b:12s} : "
            f"{delta:+.8f} Ry "
            f"(abs={abs_delta:.8f})"
        )

    print()
    if all(b < a for a, b in zip(deltas, deltas[1:])):
        print("[INTERPRETATION] Ecarts consecutifs decroissants")
    elif all(b > a for a, b in zip(deltas, deltas[1:])):
        print("[INTERPRETATION] Ecarts consecutifs croissants")
    else:
        print("[INTERPRETATION] Ecarts non monotones")

    print(
        "[INFO] Cette phase ne modifie pas le statut de stabilite "
        "et ne constitue pas une validation scientifique."
    )


print("=" * 78)
print("PHASE 78.8 — AUDIT DIFFERENTIEL QE")
print("=" * 78)
print("[MODE] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier QE modifié")

cutoff = [
    ("60 Ry", BASE / "run_60Ry/TiFeH2_cutoff_60.out"),
    ("80 Ry", BASE / "run_80Ry/TiFeH2_cutoff_80.out"),
    ("100 Ry", BASE / "run_100Ry/TiFeH2_cutoff_100.out"),
]

kpoints = [
    ("2x2x2", BASE / "run_kpoints_2x2x2/TiFeH2_kpoints_2.out"),
    ("3x3x3", BASE / "run_kpoints_3x3x3/TiFeH2_kpoints_3.out"),
    ("4x4x4", BASE / "run_kpoints_4x4x4/TiFeH2_kpoints_4.out"),
]

smearing = [
    ("0.001 Ry", BASE / "smearing_tests/degauss_0.001Ry/TiFeH2_degauss_0.001Ry.out"),
    ("0.002 Ry", BASE / "smearing_tests/degauss_0.002Ry/TiFeH2_degauss_0.002Ry.out"),
    ("0.005 Ry", BASE / "smearing_tests/degauss_0.005Ry/TiFeH2_degauss_0.005Ry.out"),
    ("0.010 Ry", BASE / "smearing_tests/degauss_0.010Ry/TiFeH2_degauss_0.010Ry.out"),
]

analyze("CUTOFF", cutoff)
analyze("K-POINTS", kpoints)
analyze("SMEARING", smearing)

print()
print("=" * 78)
print("CONCLUSION PHASE 78.8")
print("=" * 78)
print("[OK] Analyse différentielle terminée")
print("[OK] Aucun calcul supplémentaire")
print("[OK] Aucun résultat QE modifié")
