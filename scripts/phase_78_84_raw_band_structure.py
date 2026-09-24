#!/usr/bin/env python3

import sys
from pathlib import Path

sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

# Lignes déjà identifiées par l'audit brut 78.79.
TARGETS = {
    4: {
        "UP": [447, 458, 482, 530, 554, 650, 690],
        "DOWN": [690, 701, 725, 773, 797, 893, 933],
    },
    5: {
        "UP": [497, 508, 532, 580, 636, 756, 812],
        "DOWN": [812, 823, 847, 895, 951, 1071, 1127],
    },
}


def show(lines, center, radius=8):

    start = max(1, center - radius)
    end = min(len(lines), center + radius)

    print()
    print("-" * 78)
    print(
        f"CONTEXTE L{center} "
        f"(lignes {start} → {end})"
    )
    print("-" * 78)

    for n in range(start, end + 1):

        marker = " >>> " if n == center else "     "

        print(
            f"{marker}{n:5d} | {lines[n-1]}"
        )


def analyse(grid, path):

    print()
    print("=" * 78)
    print(f"PHASE 78.84 — RAW BAND STRUCTURE — {grid}³")
    print("=" * 78)

    if not path.exists():
        print("[ERROR] Fichier absent.")
        return

    lines = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Total lignes : {len(lines)}")
    print()
    print(
        "[INFO] Inspection READ-ONLY de zones ciblées."
    )

    for spin in ("UP", "DOWN"):

        print()
        print("=" * 78)
        print(f"SPIN {spin}")
        print("=" * 78)

        for line_number in TARGETS[grid][spin]:

            show(
                lines,
                line_number,
                radius=7,
            )


def main():

    print("=" * 78)
    print("PHASE 78.84 — RAW BAND STRUCTURE INSPECTION")
    print("=" * 78)
    print("[INFO] MODE = READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun recalcul")
    print("[INFO] Aucun fichier scientifique modifié")

    analyse(
        4,
        FILES[4],
    )

    analyse(
        5,
        FILES[5],
    )

    print()
    print("=" * 78)
    print("PHASE 78.84 — FIN")
    print("=" * 78)


if __name__ == "__main__":
    main()
