#!/usr/bin/env python3

import re
import sys
from pathlib import Path

sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

BASE = Path("/home/hk/HydroMatAI")

FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

EF_RE = re.compile(
    r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
    re.I
)

HEADER_RE = re.compile(
    r"^\s*k\s*=.*bands\s*\(ev\)\s*:\s*$",
    re.I
)

NUMERIC_RE = re.compile(
    r"^\s*[-+0-9.eE]+(?:\s+[-+0-9.eE]+)*\s*$"
)


def parse_file(path):
    lines = path.read_text(errors="replace").splitlines()

    ef = None
    for line in lines:
        m = EF_RE.search(line)
        if m:
            ef = float(m.group(1))

    spin_sections = []
    for i, line in enumerate(lines):
        if "------ SPIN UP" in line:
            spin_sections.append(("UP", i))
        elif "------ SPIN DOWN" in line:
            spin_sections.append(("DOWN", i))

    results = {}

    for spin_index, (spin, start) in enumerate(spin_sections):
        end = (
            spin_sections[spin_index + 1][1]
            if spin_index + 1 < len(spin_sections)
            else len(lines)
        )

        blocks = []
        i = start

        while i < end:
            if HEADER_RE.match(lines[i]):
                header_line = i + 1

                # QE imprime normalement une ligne vide
                # puis les 5 lignes numériques.
                j = i + 1

                while j < end and not lines[j].strip():
                    j += 1

                values = []
                numeric_lines = []

                while j < end and len(numeric_lines) < 5:
                    if NUMERIC_RE.match(lines[j]):
                        vals = [
                            float(x)
                            for x in lines[j].split()
                        ]
                        numeric_lines.append(j + 1)
                        values.extend(vals)
                        j += 1
                    elif not lines[j].strip():
                        if numeric_lines:
                            break
                        j += 1
                    else:
                        break

                valid = (
                    len(numeric_lines) == 5
                    and len(values) == 36
                )

                blocks.append({
                    "header": header_line,
                    "nvalues": len(values),
                    "numeric_lines": numeric_lines,
                    "values": values,
                    "valid": valid,
                })

            i += 1

        results[spin] = blocks

    return lines, ef, results


print("=" * 78)
print("PHASE 78.87 — EXACT FULL BAND PARSER")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

for mesh, path in FILES.items():

    print()
    print("=" * 78)
    print(f"PHASE 78.87 — {mesh}³")
    print("=" * 78)

    if not path.exists():
        print(f"[ERROR] Fichier absent : {path}")
        continue

    lines, ef, parsed = parse_file(path)

    print(f"[INFO] Fichier : {path}")
    print(f"[INFO] Lignes  : {len(lines)}")
    print(f"[OK] EF = {ef:.6f} eV")

    for spin in ("UP", "DOWN"):
        blocks = parsed.get(spin, [])

        valid = sum(b["valid"] for b in blocks)

        print()
        print(
            f"[{spin}] blocs détectés : "
            f"{len(blocks)}"
        )

        print(
            f"[{spin}] blocs valides   : "
            f"{valid}/{len(blocks)}"
        )

        if blocks:
            invalid = [
                (i + 1, b["header"], b["nvalues"])
                for i, b in enumerate(blocks)
                if not b["valid"]
            ]

            if invalid:
                print(
                    f"[WARN] {len(invalid)} bloc(s) invalides"
                )
                for idx, line, n in invalid[:10]:
                    print(
                        f"  bloc={idx:2d} "
                        f"L{line:4d} "
                        f"n={n}"
                    )

    up = parsed.get("UP", [])
    down = parsed.get("DOWN", [])

    total_blocks = len(up) + len(down)
    total_valid = (
        sum(b["valid"] for b in up)
        + sum(b["valid"] for b in down)
    )

    total_values = (
        sum(len(b["values"]) for b in up)
        + sum(len(b["values"]) for b in down)
    )

    print()
    print("[RESULT]")
    print(
        f"Blocs totaux : {total_blocks}"
    )
    print(
        f"Blocs valides : {total_valid}/{total_blocks}"
    )
    print(
        f"Valeurs extraites : {total_values}"
    )

    expected = 60 * 36 if mesh == 4 else 78 * 36

    if total_valid == total_blocks and total_values == expected:
        print(
            f"[PASS] EXTRACTION COMPLETE : "
            f"{expected}/{expected} valeurs"
        )
    else:
        print(
            f"[WARN] EXTRACTION INCOMPLETE : "
            f"attendu={expected}"
        )

print()
print("=" * 78)
print("PHASE 78.87 — FIN")
print("=" * 78)
print("[INFO] Aucun calcul QE exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
