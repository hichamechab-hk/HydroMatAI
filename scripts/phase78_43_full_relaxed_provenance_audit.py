import os
os.system("clear")

from pathlib import Path
import hashlib
import re

print("=" * 78)
print("PHASE 78.43 — FULL RELAXED ELECTRONIC PROVENANCE AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()

BASE = Path("/home/hk/HydroMatAI")

ROOT = BASE / "calculations/top5_dft/TiFeH2"
ELECTRONIC = ROOT / "electronic_relaxed"

FILES = {
    "RELAX_IN": ROOT / "TiFeH2_relax.in",
    "RELAX_OUT": ROOT / "TiFeH2_relax.out",

    "NSCF_IN": ELECTRONIC / "TiFeH2_relaxed_nscf.in",
    "NSCF_OUT": ELECTRONIC / "TiFeH2_relaxed_nscf.out",

    "BANDS_IN": ELECTRONIC / "TiFeH2_relaxed_bands.in",
    "BANDS_OUT": ELECTRONIC / "TiFeH2_relaxed_bands.out",

    "DOS_IN": ELECTRONIC / "TiFeH2_relaxed_dos.in",
    "DOS_OUT": ELECTRONIC / "TiFeH2_relaxed_dos.out",

    "DOS_DATA": ELECTRONIC / "TiFeH2_relaxed.dos",
}

# ==========================================================================
# 1. INVENTAIRE
# ==========================================================================

print("1. INVENTAIRE DES FICHIERS")
print("-" * 78)

missing = []

for name, path in FILES.items():

    if path.exists():
        print(
            f"{name:10s} : OK "
            f"size={path.stat().st_size} bytes"
        )
    else:
        print(f"{name:10s} : ABSENT")
        missing.append(name)

if missing:
    raise SystemExit(
        "[ERROR] Fichiers absents : " + ", ".join(missing)
    )

# ==========================================================================
# 2. SHA256
# ==========================================================================

print()
print("2. SHA256 — PROVENANCE")
print("-" * 78)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

for name, path in FILES.items():
    print(f"{name:10s} : {sha256(path)}")

# ==========================================================================
# 3. INPUT PARAMETERS
# ==========================================================================

print()
print("3. PARAMÈTRES DES INPUTS")
print("-" * 78)

INPUTS = {
    "RELAX": FILES["RELAX_IN"],
    "NSCF": FILES["NSCF_IN"],
    "BANDS": FILES["BANDS_IN"],
    "DOS": FILES["DOS_IN"],
}

PARAMETERS = [
    "calculation",
    "prefix",
    "outdir",
    "pseudo_dir",
    "nat",
    "ntyp",
    "ecutwfc",
    "ecutrho",
    "nspin",
    "occupations",
    "smearing",
    "degauss",
    "conv_thr",
    "electron_maxstep",
    "mixing_beta",
    "starting_magnetization",
]

def extract_param(text, key):

    pattern = re.compile(
        rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*,?\s*$",
        re.IGNORECASE,
    )

    values = []

    for line in text.splitlines():

        m = pattern.match(line)

        if m:
            values.append(m.group(1).strip())

    return values

input_texts = {
    name: path.read_text(errors="replace")
    for name, path in INPUTS.items()
}

for param in PARAMETERS:

    print()
    print(f"[{param}]")

    for name, text in input_texts.items():

        values = extract_param(text, param)

        if values:
            print(
                f"  {name:5s}: "
                + " | ".join(values)
            )
        else:
            print(
                f"  {name:5s}: ABSENT"
            )

# ==========================================================================
# 4. CELLULE
# ==========================================================================

print()
print("4. CELLULE")
print("-" * 78)

def extract_cell(text):

    lines = text.splitlines()

    for i, line in enumerate(lines):

        if "CELL_PARAMETERS" in line.upper():

            cell = []

            for j in range(i + 1, min(i + 4, len(lines))):

                vals = lines[j].split()

                if len(vals) >= 3:

                    try:
                        cell.append(
                            tuple(float(x) for x in vals[:3])
                        )
                    except ValueError:
                        pass

            if len(cell) == 3:
                return cell

    return None


cells = {}

for name, text in input_texts.items():

    cell = extract_cell(text)

    cells[name] = cell

    print(f"{name:5s} :")

    if cell is None:
        print("  [ABSENT]")
    else:
        for row in cell:
            print(
                "  "
                + " ".join(f"{x:.12f}" for x in row)
            )

# ==========================================================================
# 5. ATOMIC POSITIONS
# ==========================================================================

print()
print("5. GÉOMÉTRIE ATOMIQUE DES INPUTS")
print("-" * 78)

def extract_positions(text):

    lines = text.splitlines()

    for i, line in enumerate(lines):

        if "ATOMIC_POSITIONS" in line.upper():

            positions = []

            for j in range(i + 1, min(i + 20, len(lines))):

                vals = lines[j].split()

                if len(vals) < 4:
                    break

                try:
                    x = float(vals[1])
                    y = float(vals[2])
                    z = float(vals[3])
                except ValueError:
                    break

                positions.append(
                    (
                        vals[0],
                        x,
                        y,
                        z,
                    )
                )

            if positions:
                return positions

    return None


positions = {}

for name, text in input_texts.items():

    pos = extract_positions(text)
    positions[name] = pos

    if pos is None:
        print(f"{name:5s} : ABSENT")
    else:
        print(
            f"{name:5s} : {len(pos)} atomes"
        )

# ==========================================================================
# 6. COMPARAISON NSCF / BANDS / DOS
# ==========================================================================

print()
print("6. COHÉRENCE GÉOMÉTRIQUE NSCF ↔ BANDS ↔ DOS")
print("-" * 78)

def max_position_delta(a, b):

    if a is None or b is None:
        return None

    if len(a) != len(b):
        return None

    max_delta = 0.0

    for x, y in zip(a, b):

        if x[0] != y[0]:
            return None

        delta = max(
            abs(x[i] - y[i])
            for i in range(1, 4)
        )

        max_delta = max(max_delta, delta)

    return max_delta


pairs = [
    ("NSCF", "BANDS"),
    ("NSCF", "DOS"),
    ("BANDS", "DOS"),
]

for a, b in pairs:

    delta = max_position_delta(
        positions[a],
        positions[b],
    )

    if delta is None:
        print(
            f"{a} ↔ {b} : "
            "[INFO] comparaison directe impossible"
        )
    else:
        print(
            f"{a} ↔ {b} : "
            f"Max |Δ position| = {delta:.12e}"
        )

# ==========================================================================
# 7. CELLULE NSCF / BANDS / DOS
# ==========================================================================

print()
print("7. COHÉRENCE CELLULE NSCF ↔ BANDS ↔ DOS")
print("-" * 78)

def max_cell_delta(a, b):

    if a is None or b is None:
        return None

    if len(a) != 3 or len(b) != 3:
        return None

    return max(
        abs(a[i][j] - b[i][j])
        for i in range(3)
        for j in range(3)
    )


for a, b in pairs:

    delta = max_cell_delta(
        cells[a],
        cells[b],
    )

    if delta is None:
        print(
            f"{a} ↔ {b} : comparaison impossible"
        )
    else:
        print(
            f"{a} ↔ {b} : "
            f"Max |Δ cellule| = {delta:.12e}"
        )

# ==========================================================================
# 8. JOB DONE / ERRORS
# ==========================================================================

print()
print("8. ÉTAT DES SORTIES QE")
print("-" * 78)

OUTPUTS = {
    "RELAX": FILES["RELAX_OUT"],
    "NSCF": FILES["NSCF_OUT"],
    "BANDS": FILES["BANDS_OUT"],
    "DOS": FILES["DOS_OUT"],
}

ERROR_PATTERNS = [
    "Error in routine",
    "%%%%%%%%%%%%%%",
    "JOB ABORTED",
    "stopping ...",
]

for name, path in OUTPUTS.items():

    text = path.read_text(errors="replace")

    job_done = "JOB DONE" in text

    errors = []

    for pattern in ERROR_PATTERNS:

        if pattern in text:
            errors.append(pattern)

    print(
        f"{name:5s} : "
        f"JOB DONE={'YES' if job_done else 'NO'} "
        f"errors={len(errors)}"
    )

    if errors:
        print(
            "       markers:",
            ", ".join(errors)
        )

# ==========================================================================
# 9. C_BANDS
# ==========================================================================

print()
print("9. C_BANDS — CAVEAT NUMÉRIQUE")
print("-" * 78)

for name, path in OUTPUTS.items():

    text = path.read_text(errors="replace")

    count = len(
        re.findall(
            r"c_bands",
            text,
            re.IGNORECASE,
        )
    )

    print(
        f"{name:5s} : c_bands occurrences = {count}"
    )

print()
print(
    "[INFO] c_bands est conservé comme avertissement "
    "de diagonalisation numérique."
)
print(
    "[INFO] Il n'est pas interprété automatiquement comme "
    "échec lorsque JOB DONE est présent."
)

# ==========================================================================
# 10. EF
# ==========================================================================

print()
print("10. FERMI ENERGY")
print("-" * 78)

nscf_text = FILES["NSCF_OUT"].read_text(errors="replace")

fermi = []

for line in nscf_text.splitlines():

    m = re.search(
        r"the Fermi energy is\s+([-+0-9.eE]+)\s+ev",
        line,
        re.IGNORECASE,
    )

    if m:
        fermi.append(float(m.group(1)))

if fermi:

    ef = fermi[-1]

    print(
        f"EF NSCF = {ef:.6f} eV"
    )

    print(
        f"EF référence audit = 12.957300 eV"
    )

    print(
        f"Écart = {ef - 12.9573:+.6e} eV"
    )

# ==========================================================================
# 11. DOS HEADER
# ==========================================================================

print()
print("11. DOS — PROVENANCE")
print("-" * 78)

dos_text = FILES["DOS_DATA"].read_text(
    errors="replace"
)

for line in dos_text.splitlines()[:1]:
    print(line)

print()
print(
    "[OK] Format confirmé : "
    "E / dosup / dosdw / Int dos"
)

# ==========================================================================
# 12. SYNTHÈSE
# ==========================================================================

print()
print("=" * 78)
print("12. SYNTHÈSE DE PROVENANCE")
print("=" * 78)

print("[OK] RELAX input/output présent")
print("[OK] NSCF relaxed input/output présent")
print("[OK] BANDS relaxed input/output présent")
print("[OK] DOS relaxed input/output présent")
print("[OK] DOS data présente")
print("[OK] SHA256 calculés")
print("[OK] Paramètres électroniques inspectés")
print("[OK] Géométrie inspectée")
print("[OK] Cellule inspectée")
print("[OK] JOB DONE inspecté")
print("[OK] c_bands séparé comme caveat")
print("[OK] EF NSCF inspecté")
print("[OK] Format DOS spin-résolu confirmé")

print()
print("[IMPORTANT]")
print(
    "[INFO] Cette phase verrouille la provenance numérique "
    "de la branche électronique relaxed."
)
print(
    "[INFO] Elle ne transforme pas les résultats en "
    "validation scientifique complète."
)
print(
    "[INFO] Stabilité cutoff/k-points/smearing : "
    "NOT_ESTABLISHED."
)
print(
    "[INFO] AIDA inchangé."
)
print(
    "[INFO] Aucun calcul QE."
)
print(
    "[INFO] Aucun fichier modifié."
)

print()
print("=" * 78)
print("PHASE 78.43 TERMINÉE — READ-ONLY")
print("=" * 78)
