from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"

GROUPS = {
    "CUTOFF": [
        BASE / "cutoff_60Ry_2x2x2.in",
        BASE / "cutoff_80Ry_2x2x2.in",
        BASE / "cutoff_100Ry_2x2x2.in",
    ],
    "KPOINTS": [
        BASE / "kpoints_2x2x2_60Ry.in",
        BASE / "kpoints_3x3x3_60Ry.in",
        BASE / "kpoints_4x4x4_60Ry.in",
    ],
    "SMEARING": [
        BASE / "smearing_tests/degauss_0.001Ry/TiFeH2_degauss_0.001Ry.in",
        BASE / "smearing_tests/degauss_0.002Ry/TiFeH2_degauss_0.002Ry.in",
        BASE / "smearing_tests/degauss_0.005Ry/TiFeH2_degauss_0.005Ry.in",
        BASE / "smearing_tests/degauss_0.010Ry/TiFeH2_degauss_0.010Ry.in",
    ],
}


def read(path: Path) -> str:
    return path.read_text(errors="replace")


def normalize(text: str) -> list[str]:
    lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("!"):
            continue

        lines.append(stripped)

    return lines


def parameter_map(text: str) -> dict[str, str]:
    result = {}

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("!"):
            continue

        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_]*(?:\([^)]+\))?)\s*=\s*([^,!]+)",
            line,
        )

        if m:
            key = m.group(1).lower()
            value = m.group(2).strip()
            result[key] = value

    return result


def compare(group: str, paths: list[Path]) -> None:
    print()
    print("=" * 78)
    print(f"DEEP DIFF — {group}")
    print("=" * 78)

    for path in paths:
        if not path.exists():
            raise SystemExit(f"[FAIL] Fichier absent : {path}")

    maps = [(path, parameter_map(read(path))) for path in paths]

    all_keys = sorted(
        {
            key
            for _, mapping in maps
            for key in mapping
        }
    )

    print()
    print("PARAMETRES")

    for key in all_keys:
        values = {
            mapping.get(key)
            for _, mapping in maps
        }

        if len(values) == 1:
            print(f"[SAME] {key} = {next(iter(values))}")
        else:
            print(f"[DIFF] {key}")

            for path, mapping in maps:
                print(
                    f"       {path.name}: "
                    f"{mapping.get(key, '<ABSENT>')}"
                )

    print()
    print("LIGNES STRUCTURELLES")

    normalized = [(path, normalize(read(path))) for path in paths]

    reference = normalized[0][1]

    for path, lines in normalized[1:]:
        differences = []

        max_len = max(len(reference), len(lines))

        for i in range(max_len):
            a = reference[i] if i < len(reference) else "<ABSENT>"
            b = lines[i] if i < len(lines) else "<ABSENT>"

            if a != b:
                differences.append((i + 1, a, b))

        print()
        print(f"{paths[0].name} VS {path.name}")

        if not differences:
            print("[OK] Aucun écart structurel")
        else:
            for line_no, a, b in differences:
                print(f"[DIFF ligne {line_no}]")
                print(f"  REF : {a}")
                print(f"  TEST: {b}")


print("=" * 78)
print("PHASE 78.10 — AUDIT PROFOND DES INPUTS QE")
print("=" * 78)
print("[MODE] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier QE modifié")

for group, paths in GROUPS.items():
    compare(group, paths)

print()
print("=" * 78)
print("CONTROLE SPECIFIQUE DU SCF")
print("=" * 78)

keys = [
    "conv_thr",
    "electron_maxstep",
    "mixing_beta",
    "mixing_mode",
    "diagonalization",
    "startingwfc",
    "startingpot",
    "occupations",
    "smearing",
    "degauss",
]

for group, paths in GROUPS.items():

    print()
    print(f"--- {group} ---")

    for path in paths:
        mapping = parameter_map(read(path))

        print(path.name)

        for key in keys:
            print(
                f"  {key:20s} = "
                f"{mapping.get(key, '<ABSENT>')}"
            )

print()
print("=" * 78)
print("CONTROLE conv_thr")
print("=" * 78)

for group, paths in GROUPS.items():
    values = {
        parameter_map(read(path)).get("conv_thr")
        for path in paths
    }

    print(f"{group}: conv_thr = {sorted(values)}")

print()
print("=" * 78)
print("CONCLUSION PHASE 78.10")
print("=" * 78)
print("[OK] Audit profond terminé")
print("[OK] Aucun calcul QE exécuté")
print("[OK] Aucun fichier modifié")
print("[INFO] Aucune nouvelle campagne ne doit être lancée avant interprétation")
