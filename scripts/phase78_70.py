#!/usr/bin/env python3

from pathlib import Path
import re

print("\033c", end="")

print("=" * 78)
print("PHASE 78.70 — AUDIT DES K-POINTS ET DE LA SYMÉTRIE QE")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print("[INFO] Cible : TiFeH2 / 140 Ry / 560 Ry / k=4→8")
print()

BASE = Path(
    "/home/hk/HydroMatAI/calculations/"
    "phase78_61_convergence/TiFeH2"
)

OUTS = {
    4: BASE / "ecut140_rho560_k444.out",
    5: BASE / "ecut140_rho560_k555.out",
    6: BASE / "ecut140_rho560_k666.out",
    7: BASE / "ecut140_rho560_k777.out",
    8: BASE / "ecut140_rho560_k888_phase78_63.out",
}

def sections(text, patterns):
    result = []

    for i, line in enumerate(text.splitlines()):
        for pattern in patterns:
            if re.search(pattern, line, re.I):
                result.append((i + 1, line.rstrip()))
                break

    return result


print("===== 1. INVENTAIRE DES SORTIES =====")
print("-" * 78)

texts = {}

for k, path in OUTS.items():

    if path.exists():
        texts[k] = path.read_text(errors="replace")
        print(f"{k}³ : OK  {path.name}")
    else:
        print(f"{k}³ : ABSENT")


print()
print("===== 2. INFORMATIONS K-POINTS =====")
print("-" * 78)

for k, text in texts.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    matches = sections(
        text,
        [
            r"number of k points",
            r"Number of k-points",
            r"Monkhorst",
            r"Marzari",
            r"shift",
            r"symmetr",
            r"symmet",
        ]
    )

    seen = set()

    for line_no, line in matches:

        key = line.strip()

        if key not in seen:
            print(f"ligne {line_no}: {key}")
            seen.add(key)


print()
print("===== 3. SYMÉTRIES CRISTALLOGRAPHIQUES =====")
print("-" * 78)

for k, text in texts.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    matches = sections(
        text,
        [
            r"Symmetry",
            r"symmetries",
            r"symmetry operations",
            r"point group",
            r"space group",
            r"bravais",
            r"inversion",
        ]
    )

    if matches:

        seen = set()

        for line_no, line in matches:

            key = line.strip()

            if key not in seen:
                print(f"ligne {line_no}: {key}")
                seen.add(key)

    else:
        print("[INFO] Aucun message de symétrie explicite trouvé.")


print()
print("===== 4. OPTIONS SUSCEPTIBLES D'AFFECTER LES K-POINTS =====")
print("-" * 78)

patterns = [
    r"\bnosym\b",
    r"\bnoinv\b",
    r"\bforce_symmorphic\b",
    r"\bspace_group\b",
    r"\boccupations\b",
    r"\bsmearing\b",
    r"\bdegauss\b",
]

for k, text in texts.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    lines = text.splitlines()

    found = False

    for i, line in enumerate(lines):

        for pattern in patterns:

            if re.search(pattern, line, re.I):

                print(f"ligne {i + 1}: {line.strip()}")
                found = True
                break

    if not found:
        print("[INFO] Aucun de ces paramètres trouvé explicitement.")


print()
print("===== 5. EXTRACTION DES LIGNES DE K-POINTS =====")
print("-" * 78)

for k, text in texts.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    lines = text.splitlines()

    candidates = []

    for i, line in enumerate(lines):

        if re.search(
            r"number of k points\s*=",
            line,
            re.I
        ):
            candidates.append(i)

        elif re.search(
            r"crystal coordinates",
            line,
            re.I
        ):
            candidates.append(i)

        elif re.search(
            r"cartesian coordinates",
            line,
            re.I
        ):
            candidates.append(i)

    if not candidates:
        print("[INFO] Aucun tableau explicite de k-points détecté.")
        continue

    for idx in candidates[:5]:

        print(
            f"ligne {idx + 1}: "
            f"{lines[idx].strip()}"
        )


print()
print("===== 6. ÉNERGIES + NOMBRE DE K-POINTS =====")
print("-" * 78)

data = {}

for k, text in texts.items():

    energy_match = re.findall(
        r"!\s*total energy\s*=\s*"
        r"([-0-9.]+)\s*Ry",
        text,
        re.I
    )

    k_matches = re.findall(
        r"number of k points\s*=\s*"
        r"(\d+)",
        text,
        re.I
    )

    ef_match = re.findall(
        r"the Fermi energy is\s*"
        r"([-0-9.]+)\s*ev",
        text,
        re.I
    )

    if energy_match:

        energy = float(energy_match[-1])

    else:

        energy = None

    if k_matches:

        nk = int(k_matches[-1])

    else:

        nk = None

    if ef_match:

        ef = float(ef_match[-1])

    else:

        ef = None

    data[k] = (energy, nk, ef)

    print(
        f"{k}³ : "
        f"E={energy:.10f} Ry  "
        f"Nk={nk}  "
        f"EF={ef:.4f} eV"
    )


print()
print("===== 7. COMPARAISON PAIR / IMPAIR =====")
print("-" * 78)

for k in [4, 5, 6, 7, 8]:

    if k not in data:
        continue

    energy, nk, ef = data[k]

    parity = "PAIR" if k % 2 == 0 else "IMPAIR"

    print(
        f"{k}³ : {parity:6s}  "
        f"Nk={nk:3d}  "
        f"EF={ef:.4f} eV"
    )


print()
print("===== 8. DIAGNOSTIC =====")
print("-" * 78)

print(
    "[INFO] Cette phase ne conclut pas à la convergence."
)

print(
    "[INFO] Elle cherche à identifier si la variation "
    "4³→8³ peut être reliée au traitement des k-points "
    "par QE."
)

print(
    "[INFO] Aucun calcul supplémentaire n'est lancé."
)

print()
print("=" * 78)
print("PHASE 78.70 TERMINÉE")
print("=" * 78)
