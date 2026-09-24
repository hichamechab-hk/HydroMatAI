#!/usr/bin/env python3

from pathlib import Path
import re
import hashlib

print("\033c", end="")

print("=" * 78)
print("PHASE 78.69 — AUDIT STRUCTUREL COMPLET 140/560 k=4→8")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] Cible : TiFeH2 / ecutwfc=140 Ry / ecutrho=560 Ry")
print()

BASE = Path(
    "/home/hk/HydroMatAI/calculations/phase78_61_convergence/TiFeH2"
)

FILES = {
    4: BASE / "ecut140_rho560_k444.in",
    5: BASE / "ecut140_rho560_k555.in",
    6: BASE / "ecut140_rho560_k666.in",
    7: BASE / "ecut140_rho560_k777.in",
    8: BASE / "ecut140_rho560_k888_phase78_63.in",
}

OUTS = {
    4: BASE / "ecut140_rho560_k444.out",
    5: BASE / "ecut140_rho560_k555.out",
    6: BASE / "ecut140_rho560_k666.out",
    7: BASE / "ecut140_rho560_k777.out",
    8: BASE / "ecut140_rho560_k888_phase78_63.out",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def get_value(text, pattern, default="NOT_FOUND"):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else default

def get_block(text, start_pattern, end_patterns):
    lines = text.splitlines()
    start = None

    for i, line in enumerate(lines):
        if re.search(start_pattern, line, re.I):
            start = i
            break

    if start is None:
        return []

    block = []

    for line in lines[start:]:
        if block and any(
            re.search(p, line, re.I)
            for p in end_patterns
        ):
            break
        block.append(line)

    return block

print("===== 1. INVENTAIRE =====")
print("-" * 78)

for k, path in FILES.items():
    print(
        f"k={k}: "
        f"{'OK' if path.exists() else 'ABSENT'}  "
        f"{path.name}"
    )

print()

print("===== 2. HASH SHA256 DES INPUTS =====")
print("-" * 78)

for k, path in FILES.items():
    if path.exists():
        print(f"{k}³ : {sha256(path)}")

print()

print("===== 3. PARAMÈTRES & K-POINTS DES INPUTS =====")
print("-" * 78)

records = {}

for k, path in FILES.items():

    if not path.exists():
        continue

    text = path.read_text(errors="replace")
    records[k] = text

    print()
    print(f"--- {k}x{k}x{k} ---")

    patterns = {
        "prefix":
            r"\bprefix\s*=\s*['\"]([^'\"]+)",
        "pseudo_dir":
            r"\bpseudo_dir\s*=\s*['\"]([^'\"]+)",
        "ecutwfc":
            r"\becutwfc\s*=\s*([0-9.]+)",
        "ecutrho":
            r"\becutrho\s*=\s*([0-9.]+)",
        "occupations":
            r"\boccupations\s*=\s*['\"]([^'\"]+)",
        "smearing":
            r"\bsmearing\s*=\s*['\"]([^'\"]+)",
        "degauss":
            r"\bdegauss\s*=\s*([0-9.]+)",
        "nspin":
            r"\bnspin\s*=\s*(\d+)",
        "nat":
            r"\bnat\s*=\s*(\d+)",
        "ntyp":
            r"\bntyp\s*=\s*(\d+)",
    }

    for name, pattern in patterns.items():
        print(
            f"{name:15s}: "
            f"{get_value(text, pattern)}"
        )

    print()
    print("K_POINTS block:")

    kp = get_block(
        text,
        r"^\s*K_POINTS",
        [
            r"^\s*&",
            r"^\s*[A-Z_]+\s*="
        ]
    )

    if kp:
        for line in kp:
            print("  " + line)
    else:
        print("  [WARN] K_POINTS non trouvé")


print()
print("===== 4. COMPARAISON DES PARAMÈTRES COMMUNS =====")
print("-" * 78)

common_patterns = {
    "prefix":
        r"\bprefix\s*=\s*['\"]([^'\"]+)",
    "pseudo_dir":
        r"\bpseudo_dir\s*=\s*['\"]([^'\"]+)",
    "ecutwfc":
        r"\becutwfc\s*=\s*([0-9.]+)",
    "ecutrho":
        r"\becutrho\s*=\s*([0-9.]+)",
    "occupations":
        r"\boccupations\s*=\s*['\"]([^'\"]+)",
    "smearing":
        r"\bsmearing\s*=\s*['\"]([^'\"]+)",
    "degauss":
        r"\bdegauss\s*=\s*([0-9.]+)",
    "nspin":
        r"\bnspin\s*=\s*(\d+)",
    "nat":
        r"\bnat\s*=\s*(\d+)",
    "ntyp":
        r"\bntyp\s*=\s*(\d+)",
}

for name, pattern in common_patterns.items():

    vals = {}

    for k, text in records.items():
        vals[k] = get_value(text, pattern)

    unique = set(vals.values())

    status = "IDENTIQUE" if len(unique) == 1 else "DIFFÉRENT"

    print(f"{name:15s}: {status}")

    if len(unique) != 1:
        for k, value in vals.items():
            print(f"    {k}³ -> {value}")


print()
print("===== 5. CELL / ATOMIC_POSITIONS =====")
print("-" * 78)

for k, text in records.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    cell = get_block(
        text,
        r"^\s*CELL_PARAMETERS",
        [
            r"^\s*ATOMIC_POSITIONS",
            r"^\s*K_POINTS",
            r"^\s*&"
        ]
    )

    atoms = get_block(
        text,
        r"^\s*ATOMIC_POSITIONS",
        [
            r"^\s*K_POINTS",
            r"^\s*&"
        ]
    )

    print("[CELL_PARAMETERS]")
    for line in cell:
        print("  " + line)

    print("[ATOMIC_POSITIONS]")
    for line in atoms:
        print("  " + line)


print()
print("===== 6. COMPARAISON EXACTE STRUCTURE =====")
print("-" * 78)

def normalize_structure(text):

    lines = text.splitlines()

    selected = []
    mode = None

    for line in lines:

        if re.match(r"^\s*CELL_PARAMETERS", line, re.I):
            mode = "cell"
            selected.append(line.strip())
            continue

        if re.match(r"^\s*ATOMIC_POSITIONS", line, re.I):
            mode = "atoms"
            selected.append(line.strip())
            continue

        if re.match(r"^\s*K_POINTS", line, re.I):
            mode = None

        if mode:
            selected.append(line.strip())

    return "\n".join(selected)

structures = {}

for k, text in records.items():
    structures[k] = normalize_structure(text)

reference = structures.get(4)

if reference is not None:

    for k in sorted(structures):
        same = structures[k] == reference
        print(
            f"{k}³ vs 4³ : "
            f"{'IDENTIQUE' if same else 'DIFFÉRENT'}"
        )


print()
print("===== 7. PARAMÈTRES EFFECTIVEMENT RAPPORTÉS PAR QE =====")
print("-" * 78)

for k, path in OUTS.items():

    print()
    print(f"--- {k}x{k}x{k} ---")

    if not path.exists():
        print("[WARN] OUT absent")
        continue

    text = path.read_text(errors="replace")

    patterns = [
        r"number of atoms/cell\s*=\s*(.*)",
        r"number of atomic types\s*=\s*(.*)",
        r"number of electrons\s*=\s*(.*)",
        r"number of Kohn-Sham states\s*=\s*(.*)",
        r"kinetic-energy cutoff\s*=\s*(.*)",
        r"charge density cutoff\s*=\s*(.*)",
        r"number of k points\s*=\s*(.*)",
        r"the Fermi energy is\s*(.*)",
    ]

    for pattern in patterns:

        m = re.search(pattern, text, re.I)

        if m:
            print("  " + m.group(0).strip())


print()
print("===== 8. WARNINGS QE =====")
print("-" * 78)

for k, path in OUTS.items():

    if not path.exists():
        continue

    text = path.read_text(errors="replace")

    warnings = [
        line.strip()
        for line in text.splitlines()
        if "warning" in line.lower()
    ]

    print()
    print(f"{k}³ : {len(warnings)} warning(s)")

    for line in warnings[:10]:
        print("  " + line)


print()
print("===== 9. RÉSULTATS ÉNERGÉTIQUES =====")
print("-" * 78)

energies = {}

for k, path in OUTS.items():

    if not path.exists():
        continue

    text = path.read_text(errors="replace")

    m = re.findall(
        r"!\s*total energy\s*=\s*([-0-9.]+)\s*Ry",
        text,
        re.I
    )

    if m:
        energies[k] = float(m[-1])
        print(
            f"{k}³ : "
            f"{energies[k]:.10f} Ry"
        )

print()
print("===== 10. DIAGNOSTIC FINAL =====")
print("-" * 78)

if energies:

    print(
        "[RESULT] Les cinq sorties sont analysées "
        "dans un cadre homogène."
    )

    if len(energies) == 5:
        print(
            "[RESULT] 5/5 énergies finales disponibles."
        )

print()
print("[IMPORTANT]")
print(
    "Cet audit ne décide PAS d'une convergence en k-points."
)
print(
    "Il vérifie uniquement que les calculs comparés "
    "sont structurellement homogènes."
)
print(
    "Aucun calcul QE n'a été lancé."
)

print()
print("=" * 78)
print("PHASE 78.69 TERMINÉE")
print("=" * 78)
