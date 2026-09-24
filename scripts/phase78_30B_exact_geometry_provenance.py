from pathlib import Path
import re
import math

ROOT = Path("/home/hk/HydroMatAI")

RELAX_OUT = ROOT / "calculations/top5_dft/TiFeH2/TiFeH2_relax.out"
CIF = ROOT / "calculations/top5_dft/TiFeH2/TiFeH2.cif"

NSCF = ROOT / (
    "calculations/top5_dft/TiFeH2/electronic_relaxed/"
    "TiFeH2_relaxed_nscf.in"
)

BANDS = ROOT / (
    "calculations/top5_dft/TiFeH2/electronic_relaxed/"
    "TiFeH2_relaxed_bands.in"
)

TOL = 1e-8


print("=" * 78)
print("PHASE 78.30B — EXACT GEOMETRY PROVENANCE")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


def read(path):
    return path.read_text(errors="replace")


def parse_atoms(lines):
    atoms = []

    for line in lines:
        parts = line.split()

        if len(parts) < 4:
            continue

        if not re.match(r"^[A-Z][a-z]?$", parts[0]):
            continue

        try:
            x = float(parts[1])
            y = float(parts[2])
            z = float(parts[3])
        except ValueError:
            continue

        atoms.append((parts[0], x, y, z))

    return atoms


def extract_final_relax_atoms(text):
    lines = text.splitlines()

    start = None
    end = None

    for i, line in enumerate(lines):
        if re.search(r"Begin final coordinates", line, re.I):
            start = i

        if start is not None and re.search(
            r"End final coordinates", line, re.I
        ):
            end = i
            break

    if start is None or end is None:
        return None

    atoms = parse_atoms(lines[start + 1:end])

    if len(atoms) != 8:
        return None

    return atoms


def extract_input_geometry(text):
    lines = text.splitlines()

    cell = None
    atoms = None

    for i, line in enumerate(lines):

        if re.match(r"^\s*CELL_PARAMETERS", line, re.I):
            block = []

            for j in range(i + 1, min(i + 4, len(lines))):
                p = lines[j].split()

                if len(p) >= 3:
                    try:
                        block.append([
                            float(p[0]),
                            float(p[1]),
                            float(p[2]),
                        ])
                    except ValueError:
                        pass

            if len(block) == 3:
                cell = block

        if re.match(r"^\s*ATOMIC_POSITIONS", line, re.I):
            block = []

            for j in range(i + 1, min(i + 9, len(lines))):
                p = lines[j].split()

                if len(p) >= 4:
                    try:
                        block.append((
                            p[0],
                            float(p[1]),
                            float(p[2]),
                            float(p[3]),
                        ))
                    except ValueError:
                        pass

            if len(block) == 8:
                atoms = block

        if cell is not None and atoms is not None:
            break

    return cell, atoms


def extract_cif(text):
    lines = text.splitlines()

    cell = {}

    atom_start = None

    for i, line in enumerate(lines):

        m = re.match(
            r"_cell_length_(a|b|c)\s+([-+0-9.Ee]+)",
            line,
            re.I,
        )

        if m:
            cell[m.group(1).lower()] = float(m.group(2))

        if re.match(r"loop_", line, re.I):
            # handled below
            pass

    headers = []
    data = []

    in_loop = False

    for i, line in enumerate(lines):

        if line.strip().lower() == "loop_":
            in_loop = True
            headers = []
            data = []
            continue

        if in_loop and line.strip().startswith("_"):
            headers.append(line.strip())
            continue

        if in_loop and headers and line.strip():
            if line.strip().startswith("_"):
                continue

            parts = line.split()

            if len(parts) >= len(headers):
                data.append(parts)

    atom_headers = [
        "_atom_site_type_symbol",
        "_atom_site_fract_x",
        "_atom_site_fract_y",
        "_atom_site_fract_z",
    ]

    if all(h in headers for h in atom_headers):

        idx = {
            h: headers.index(h)
            for h in atom_headers
        }

        atoms = []

        for row in data:
            try:
                atoms.append((
                    row[idx["_atom_site_type_symbol"]],
                    float(row[idx["_atom_site_fract_x"]]),
                    float(row[idx["_atom_site_fract_y"]]),
                    float(row[idx["_atom_site_fract_z"]]),
                ))
            except (ValueError, IndexError):
                pass

        if len(atoms) >= 8:
            return cell, atoms[-8:]

    return cell, None


def max_atom_diff(a, b):
    if len(a) != len(b):
        return math.inf

    max_diff = 0.0

    for x, y in zip(a, b):

        if x[0] != y[0]:
            return math.inf

        for k in range(1, 4):
            max_diff = max(
                max_diff,
                abs(x[k] - y[k])
            )

    return max_diff


def print_atoms(label, atoms):
    print()
    print(label)

    if atoms is None:
        print("[ABSENT]")
        return

    for a in atoms:
        print(
            f"  {a[0]:2s} "
            f"{a[1]:.12f} "
            f"{a[2]:.12f} "
            f"{a[3]:.12f}"
        )


# ----------------------------------------------------------------------
# 1. RELAX FINAL
# ----------------------------------------------------------------------

relax_text = read(RELAX_OUT)

relax_atoms = extract_final_relax_atoms(relax_text)

print("1. RELAX FINAL")
print("-" * 78)

if relax_atoms is None:
    print("[FAIL] Géométrie finale RELAX introuvable")
    raise SystemExit(1)

print("[OK] Begin final coordinates → End final coordinates")
print_atoms("Coordonnées finales RELAX", relax_atoms)


# ----------------------------------------------------------------------
# 2. NSCF / BANDS
# ----------------------------------------------------------------------

results = {}

for label, path in [
    ("NSCF", NSCF),
    ("BANDS", BANDS),
]:

    print()
    print("=" * 78)
    print(f"2. {label}")
    print("=" * 78)

    text = read(path)

    cell, atoms = extract_input_geometry(text)

    results[label] = (cell, atoms)

    print("Input :", path)
    print("Cell  :", "OK" if cell else "ABSENTE")
    print("Atoms :", "OK" if atoms else "ABSENTS")

    print_atoms(f"Coordonnées {label}", atoms)

    diff = max_atom_diff(relax_atoms, atoms)

    print()
    print(f"Max |Δ position| = {diff:.12e}")

    if diff <= TOL:
        print("[OK] Géométrie identique au RELAX final")
    else:
        print("[FAIL] Géométrie différente")


# ----------------------------------------------------------------------
# 3. CIF
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("3. CIF")
print("=" * 78)

cif_text = read(CIF)

cif_cell, cif_atoms = extract_cif(cif_text)

print("CIF :", CIF)

if cif_atoms:
    print("[OK] 8 positions atomiques CIF extraites")
    print_atoms("Coordonnées CIF", cif_atoms)

    diff = max_atom_diff(relax_atoms, cif_atoms)

    print()
    print(f"Max |Δ RELAX-CIF| = {diff:.12e}")

    if diff <= TOL:
        print("[OK] CIF = géométrie finale RELAX")
    else:
        print("[WARN] CIF différente du RELAX final")
else:
    print("[WARN] Positions atomiques CIF non extraites")


# ----------------------------------------------------------------------
# 4. CELLULE NSCF/BANDS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("4. CELLULE NSCF / BANDS")
print("=" * 78)

for label, (cell, _) in results.items():

    print()
    print(label)

    if cell is None:
        print("[ABSENT]")
        continue

    for row in cell:
        print(" ", " ".join(f"{x:.12f}" for x in row))


# ----------------------------------------------------------------------
# 5. OUTPUTS RÉELS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("5. OUTPUTS ELECTRONIQUES")
print("=" * 78)

outputs = {
    "NSCF": ROOT / (
        "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_nscf.out"
    ),
    "BANDS": ROOT / (
        "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_bands.out"
    ),
    "DOS": ROOT / (
        "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_dos.out"
    ),
}

for label, path in outputs.items():

    print()
    print(label, ":", path)

    if not path.exists():
        print("  [ABSENT]")
        continue

    text = read(path)

    job_done = bool(
        re.search(r"\bJOB DONE\b", text, re.I)
    )

    errors = re.findall(
        r"(?:Error in routine|ERROR:|fatal error|stopping)",
        text,
        re.I,
    )

    cbands = len(
        re.findall(r"c_bands:", text, re.I)
    )

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        text,
        re.I,
    )

    print("  JOB DONE       :", "YES" if job_done else "NO")
    print("  Error markers  :", len(errors))
    print("  c_bands        :", cbands)

    if fermi:
        print("  Fermi final    :", fermi[-1], "eV")

print()
print("=" * 78)
print("6. SYNTHÈSE")
print("=" * 78)

nscf_ok = (
    results["NSCF"][1] is not None
    and max_atom_diff(relax_atoms, results["NSCF"][1]) <= TOL
)

bands_ok = (
    results["BANDS"][1] is not None
    and max_atom_diff(relax_atoms, results["BANDS"][1]) <= TOL
)

print("RELAX → NSCF géométrie :", "OK" if nscf_ok else "NON")
print("RELAX → BANDS géométrie:", "OK" if bands_ok else "NON")

print()
print("[INFO] Aucun calcul QE lancé.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] Aucun statut AIDA modifié.")

print()
print("=" * 78)
print("PHASE 78.30B TERMINÉE — READ-ONLY")
print("=" * 78)
