#!/usr/bin/env python3

from pathlib import Path
import csv
import importlib.util
import re
import sys
import subprocess

ROOT = Path.cwd()

RANKING = ROOT / "reports/global_screening/TOP20_GLOBAL_H2_RANKED_V2.csv"
QE_ROOT = ROOT / "calculations/global_screening/qe"
TOP20_ROOT = QE_ROOT / "TOP20"
PSEUDO_DIR = TOP20_ROOT / "pseudo"
MANIFEST = TOP20_ROOT / "TOP20_QE_MANIFEST.csv"

print("=" * 78)
print("HYDROMATAI — PHASE 16 — GENERATION COMPLETE DES INPUTS QE")
print("=" * 78)

errors = []

# ------------------------------------------------------------------
# 1. Vérification ASE
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("1. PARSEUR CIF")
print("=" * 78)

if importlib.util.find_spec("ase") is None:
    print("[FAIL] ASE n'est pas installé dans l'environnement Python")
    print("       ASE est nécessaire pour convertir proprement les CIF.")
    errors.append("ASE absent")
    sys.exit(1)

from ase.io import read

print("[OK] ASE disponible")

# ------------------------------------------------------------------
# 2. Ranking
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. TOP20")
print("=" * 78)

if not RANKING.exists():
    print(f"[FAIL] Ranking absent : {RANKING}")
    sys.exit(1)

with RANKING.open(
    newline="",
    encoding="utf-8",
) as fh:
    ranking = list(csv.DictReader(fh))

ranking = ranking[:20]

if len(ranking) != 20:
    print(f"[FAIL] TOP20 incomplet : {len(ranking)}/20")
    sys.exit(1)

print("[OK] 20 candidats")

# ------------------------------------------------------------------
# 3. Pseudopotentiels
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("3. PSEUDOPOTENTIELS")
print("=" * 78)

PSEUDO_DIR.mkdir(parents=True, exist_ok=True)

pseudo_files = {
    p.name: p
    for p in PSEUDO_DIR.glob("*.UPF")
}

# Cherche aussi dans le répertoire QE standard déjà identifié.
qe_pseudo = Path("/home/hk/software/qe-7.5/pseudo")

if qe_pseudo.exists():
    for p in qe_pseudo.glob("*.UPF"):
        pseudo_files.setdefault(p.name, p)

print(f"[OK] {len(pseudo_files)} pseudopotentiels disponibles")

# ------------------------------------------------------------------
# 4. Recherche CIF
# ------------------------------------------------------------------
def find_cif(row):
    name = row.get("name", "").strip()
    value = row.get("cif", "").strip()

    candidates = []

    if value:
        p = Path(value)

        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.extend([
                ROOT / p,
                ROOT / "structures" / p,
                ROOT / "MOF_Library" / p,
            ])

    candidates.extend([
        ROOT / "structures" / f"{name}.cif",
        ROOT / "MOF_Library" / f"{name}.cif",
        ROOT / "MOF_Library" / name / f"{name}.cif",
    ])

    for p in candidates:
        if p.exists() and p.is_file():
            return p

    return None

# ------------------------------------------------------------------
# 5. Choix pseudo
# ------------------------------------------------------------------
def pseudo_for(element):
    element = element.strip()

    # Préférence aux fichiers déjà présents dans TOP20/pseudo.
    local = [
        name for name in pseudo_files
        if name.lower().startswith(element.lower() + ".")
    ]

    if local:
        return sorted(local)[0]

    return None

# ------------------------------------------------------------------
# 6. Génération QE
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("4. GENERATION DES 20 INPUTS")
print("=" * 78)

manifest_rows = []

for rank, row in enumerate(ranking, start=1):

    name = row.get("name", "").strip()
    score = row.get("score", "").strip()

    print(f"\n[{rank:02d}/20] {name}")

    cif = find_cif(row)

    if cif is None:
        print("[FAIL] CIF introuvable")
        errors.append(f"{name}: CIF absent")

        manifest_rows.append({
            "rank": rank,
            "name": name,
            "score": score,
            "status": "ERROR_CIF",
            "cif": "",
            "input": "",
            "elements": "",
            "nat": "",
            "ntyp": "",
            "missing_pseudo": "",
        })
        continue

    print(f"[OK] CIF : {cif}")

    try:
        atoms = read(str(cif))
    except Exception as exc:
        print(f"[FAIL] Lecture CIF : {exc}")
        errors.append(f"{name}: lecture CIF")

        manifest_rows.append({
            "rank": rank,
            "name": name,
            "score": score,
            "status": "ERROR_CIF_PARSE",
            "cif": str(cif),
            "input": "",
            "elements": "",
            "nat": "",
            "ntyp": "",
            "missing_pseudo": "",
        })
        continue

    nat = len(atoms)
    symbols = sorted(set(atoms.get_chemical_symbols()))

    print(f"[OK] Atomes : {nat}")
    print(f"[OK] Elements : {', '.join(symbols)}")

    missing = [
        element
        for element in symbols
        if pseudo_for(element) is None
    ]

    if missing:
        print(
            "[FAIL] Pseudopotentiels manquants : "
            + ", ".join(missing)
        )

        errors.append(
            f"{name}: pseudo absent ({','.join(missing)})"
        )

        manifest_rows.append({
            "rank": rank,
            "name": name,
            "score": score,
            "status": "ERROR_PSEUDO",
            "cif": str(cif),
            "input": "",
            "elements": ";".join(symbols),
            "nat": nat,
            "ntyp": len(symbols),
            "missing_pseudo": ";".join(missing),
        })
        continue

    candidate_dir = TOP20_ROOT / f"{rank:04d}_{name}"
    candidate_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_file = candidate_dir / "pw.scf.in"

    # --------------------------------------------------------------
    # Cellule
    # --------------------------------------------------------------
    if atoms.cell.rank < 3:
        print("[FAIL] Cellule périodique 3D absente")
        errors.append(f"{name}: cellule 3D absente")

        manifest_rows.append({
            "rank": rank,
            "name": name,
            "score": score,
            "status": "ERROR_CELL",
            "cif": str(cif),
            "input": "",
            "elements": ";".join(symbols),
            "nat": nat,
            "ntyp": len(symbols),
            "missing_pseudo": "",
        })
        continue

    cell = atoms.cell.array

    # --------------------------------------------------------------
    # QE input
    # --------------------------------------------------------------
    lines = []

    lines.extend([
        "&CONTROL",
        "  calculation = 'scf',",
        f"  prefix = '{name}',",
        f"  pseudo_dir = '{PSEUDO_DIR}',",
        "  outdir = './tmp',",
        "  tstress = .true.,",
        "  tprnfor = .true.,",
        "/",
        "",
        "&SYSTEM",
        "  ibrav = 0,",
        f"  nat = {nat},",
        f"  ntyp = {len(symbols)},",
        "  ecutwfc = 60.0,",
        "  ecutrho = 480.0,",
        "  occupations = 'fixed',",
        "/",
        "",
        "&ELECTRONS",
        "  conv_thr = 1.0d-8,",
        "  electron_maxstep = 200,",
        "  mixing_beta = 0.3,",
        "/",
        "",
        "ATOMIC_SPECIES",
    ])

    # Masses approximatives : QE accepte la masse atomique.
    masses = {
        "H": 1.008,
        "C": 12.011,
        "N": 14.007,
        "O": 15.999,
        "F": 18.998,
        "P": 30.974,
        "S": 32.06,
        "Cl": 35.45,
        "Cu": 63.546,
        "Zn": 65.38,
        "Ni": 58.693,
        "Co": 58.933,
        "Fe": 55.845,
        "Mn": 54.938,
        "Mg": 24.305,
        "Ca": 40.078,
        "Al": 26.982,
        "Si": 28.085,
        "Na": 22.990,
        "K": 39.098,
    }

    for element in symbols:
        pseudo = pseudo_for(element)
        mass = masses.get(element, 1.0)

        lines.append(
            f"  {element:<3} {mass:10.5f}  {pseudo}"
        )

    lines.extend([
        "",
        "CELL_PARAMETERS angstrom",
    ])

    for vector in cell:
        lines.append(
            "  " +
            "  ".join(
                f"{float(x):.12f}"
                for x in vector
            )
        )

    lines.extend([
        "",
        "ATOMIC_POSITIONS angstrom",
    ])

    positions = atoms.get_positions()
    atom_symbols = atoms.get_chemical_symbols()

    for symbol, position in zip(atom_symbols, positions):
        lines.append(
            f"  {symbol:<3} "
            + "  ".join(
                f"{float(x):.12f}"
                for x in position
            )
        )

    lines.extend([
        "",
        "K_POINTS gamma",
        "",
    ])

    input_file.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    # --------------------------------------------------------------
    # Validation interne
    # --------------------------------------------------------------
    text = input_file.read_text(
        encoding="utf-8"
    )

    required_blocks = [
        "&CONTROL",
        "&SYSTEM",
        "&ELECTRONS",
        "ATOMIC_SPECIES",
        "CELL_PARAMETERS angstrom",
        "ATOMIC_POSITIONS angstrom",
        "K_POINTS gamma",
    ]

    missing_blocks = [
        block
        for block in required_blocks
        if block not in text
    ]

    if missing_blocks:
        print(
            "[FAIL] Blocs QE manquants : "
            + ", ".join(missing_blocks)
        )
        errors.append(
            f"{name}: blocs QE incomplets"
        )

        status = "ERROR_INPUT"

    else:
        # Vérifie que le nombre de positions correspond à nat.
        position_section = text.split(
            "ATOMIC_POSITIONS angstrom",
            1
        )[1]

        position_section = position_section.split(
            "K_POINTS",
            1
        )[0]

        position_lines = [
            line.strip()
            for line in position_section.splitlines()
            if line.strip()
        ]

        valid_position_lines = [
            line
            for line in position_lines
            if re.match(
                r"^[A-Z][a-z]?\s+[-+0-9.eEdD]+\s+[-+0-9.eEdD]+\s+[-+0-9.eEdD]+",
                line,
            )
        ]

        if len(valid_position_lines) != nat:
            print(
                f"[FAIL] Positions : "
                f"{len(valid_position_lines)}/{nat}"
            )
            errors.append(
                f"{name}: nombre positions incorrect"
            )
            status = "ERROR_ATOMIC_POSITIONS"
        else:
            status = "QE_INPUT_READY"
            print("[OK] Input QE complet")
            print(f"[OK] {input_file}")

    manifest_rows.append({
        "rank": rank,
        "name": name,
        "score": score,
        "status": status,
        "cif": str(cif),
        "input": str(input_file) if status == "QE_INPUT_READY" else "",
        "elements": ";".join(symbols),
        "nat": nat,
        "ntyp": len(symbols),
        "missing_pseudo": "",
    })

# ------------------------------------------------------------------
# 7. Nouveau manifeste
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("5. MANIFESTE")
print("=" * 78)

fields = [
    "rank",
    "name",
    "score",
    "status",
    "cif",
    "input",
    "elements",
    "nat",
    "ntyp",
    "missing_pseudo",
]

with MANIFEST.open(
    "w",
    newline="",
    encoding="utf-8",
) as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(manifest_rows)

print(f"[OK] {MANIFEST}")

# ------------------------------------------------------------------
# 8. Résumé
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("6. RESUME")
print("=" * 78)

counts = {}

for row in manifest_rows:
    status = row["status"]
    counts[status] = counts.get(status, 0) + 1

for status, count in sorted(counts.items()):
    print(f"{status:<28} : {count}")

# ------------------------------------------------------------------
# 9. Tests
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("7. VALIDATION DU PROJET")
print("=" * 78)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] pytest")
else:
    print("[FAIL] pytest")
    errors.append("pytest")

result = subprocess.run(
    [sys.executable, "-m", "compileall", "-q", "src"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] compilation")
else:
    print("[FAIL] compilation")
    errors.append("compileall")

# ------------------------------------------------------------------
# 10. Conclusion
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("PHASE 16 — CONCLUSION")
print("=" * 78)

ready = sum(
    1 for row in manifest_rows
    if row["status"] == "QE_INPUT_READY"
)

print(f"\nTOP20                 : {len(manifest_rows)}/20")
print(f"Inputs QE complets    : {ready}/20")
print(f"Erreurs               : {len(errors)}")

if errors:
    print("\nBLOQUANTS :")
    for error in errors:
        print(f"  - {error}")

    print("\nSTATUT : PHASE 16 NON VALIDEE")
    print("Aucun calcul QE n'a été lancé.")
    sys.exit(1)

if ready != 20:
    print("\n[FAIL] Les 20 inputs QE ne sont pas prêts.")
    print("Aucun calcul QE ne sera lancé.")
    print("\nSTATUT : PHASE 16 NON VALIDEE")
    sys.exit(1)

print("\n[OK] 20/20 inputs QE complets")
print("[OK] Cellules cristallines présentes")
print("[OK] Positions atomiques présentes")
print("[OK] ATOMIC_SPECIES complètes")
print("[OK] Pseudopotentiels vérifiés")
print("[OK] Manifeste mis à jour")
print("[OK] Aucun calcul pw.x lancé")
print("\nSTATUT : PHASE 16 VALIDEE")
print("Prochaine étape : validation QE puis lancement DFT contrôlé.")
print("=" * 78)
