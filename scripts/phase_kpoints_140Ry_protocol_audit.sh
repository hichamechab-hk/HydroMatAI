#!/usr/bin/env bash

clear
set -euo pipefail

ROOT="/home/hk/HydroMatAI"
BASE="$ROOT/calculations/new_campaign/TiFeH2/convergence"
PY="$ROOT/.venv/bin/python"

echo "============================================================"
echo "K-POINT 140/560 Ry — AUDIT DU PROTOCOLE"
echo "============================================================"
echo "[MODE] READ-ONLY"
echo "[INFO] Aucun pw.x"
echo "[INFO] Aucune modification des fichiers QE"
echo

export PYTHONPATH="$ROOT/src"

"$PY" - <<'PY'
from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations/new_campaign/TiFeH2/convergence"

cases = {
    "3x3x3": (
        BASE / "kpoints_3x3x3_140Ry.in",
        BASE / "run_kpoints_3x3x3_140Ry/TiFeH2_kpoints_3x3x3_140.out",
    ),
    "4x4x4": (
        BASE / "kpoints_4x4x4_140Ry.in",
        BASE / "run_kpoints_4x4x4_140Ry/TiFeH2_kpoints_4x4x4_140.out",
    ),
    "5x5x5": (
        BASE / "kpoints_5x5x5_140Ry.in",
        BASE / "run_kpoints_5x5x5_140Ry/TiFeH2_kpoints_5x5x5_140.out",
    ),
}

required_input_patterns = {
    "ecutwfc": r"ecutwfc\s*=\s*([0-9.]+)",
    "ecutrho": r"ecutrho\s*=\s*([0-9.]+)",
    "nspin": r"nspin\s*=\s*(\d+)",
    "conv_thr": r"conv_thr\s*=\s*([0-9.dDeE+-]+)",
    "degauss": r"degauss\s*=\s*([0-9.dDeE+-]+)",
}

def read(path):
    return path.read_text(errors="replace") if path.exists() else ""

def value(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(1) if m else None

reference = None
all_ok = True

for grid, (inp, out) in cases.items():
    print("=" * 60)
    print(grid)
    print("=" * 60)

    if not inp.exists():
        print("[INPUT]  ABSENT")
        all_ok = False
        continue

    text = read(inp)

    values = {}
    for name, pattern in required_input_patterns.items():
        values[name] = value(pattern, text)

    k_match = re.search(
        r"K_POINTS\s+automatic\s*"
        r"\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.I,
    )

    if k_match is None:
        k_match = re.search(
            r"K_POINTS\s*\{?\s*automatic\s*\}?\s*"
            r"\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
            text,
            re.I,
        )

    kgrid = (
        tuple(map(int, k_match.groups()))
        if k_match
        else None
    )

    print("[INPUT]    OK")
    print(f"[ecutwfc]  {values['ecutwfc']} Ry")
    print(f"[ecutrho]  {values['ecutrho']} Ry")
    print(f"[nspin]    {values['nspin']}")
    print(f"[conv_thr] {values['conv_thr']}")
    print(f"[degauss]  {values['degauss']}")
    print(f"[K-GRID]   {kgrid}")

    expected = {
        "ecutwfc": "140.0",
        "ecutrho": "560.0",
        "nspin": "2",
        "conv_thr": "1.0d-10",
        "degauss": "0.01",
    }

    checks = [
        float(values["ecutwfc"]) == 140.0,
        float(values["ecutrho"]) == 560.0,
        values["nspin"] == "2",
        values["conv_thr"].lower().replace("d", "e")
        == "1.0e-10",
        float(values["degauss"]) == 0.01,
        kgrid is not None,
    ]

    if not all(checks):
        all_ok = False
        print("[PROTOCOL] FAIL")
    else:
        print("[PROTOCOL] OK")

    if reference is None:
        reference = values, kgrid
    else:
        ref_values, ref_kgrid = reference

        same_common = all(
            values[key] == ref_values[key]
            for key in values
        )

        if not same_common:
            print("[CONSISTENCY] FAIL")
            all_ok = False
        else:
            print("[CONSISTENCY] COMMON PARAMETERS OK")

    if out.exists():
        out_text = read(out)

        job_done = "JOB DONE." in out_text
        converged = (
            "convergence has been achieved" in out_text.lower()
            or "convergence achieved" in out_text.lower()
        )

        print(
            f"[OUTPUT]   {'PRESENT' if out.exists() else 'ABSENT'}"
        )
        print(
            f"[SCF]      "
            f"{'CONVERGED' if converged else 'INCOMPLETE'}"
        )
        print(
            f"[JOB DONE] "
            f"{'YES' if job_done else 'NO'}"
        )
    else:
        print("[OUTPUT]   ABSENT")

    print()

print("=" * 60)
print("CONCLUSION DE L'AUDIT DU PROTOCOLE")
print("=" * 60)

if all_ok:
    print("[PASS] Les trois inputs utilisent le protocole 140/560 Ry.")
    print("[PASS] Les paramètres SCF communs sont cohérents.")
    print("[INFO] La convergence énergétique reste déterminée")
    print("       uniquement lorsque les sorties 4x4x4 et 5x5x5")
    print("       seront terminées.")
else:
    print("[ATTENTION] Une incohérence de protocole a été détectée.")

print()
print("Aucun calcul QE n'a été lancé.")
print("Aucun fichier QE n'a été modifié.")
PY
