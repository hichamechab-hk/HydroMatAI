#!/usr/bin/env python3

from pathlib import Path
import csv
import shutil
import subprocess
import sys

ROOT = Path.cwd()

RANKING = ROOT / "reports/global_screening/TOP20_GLOBAL_H2_RANKED_V2.csv"
QE_ROOT = ROOT / "calculations/global_screening/qe"
TOP20_ROOT = QE_ROOT / "TOP20"
MANIFEST = QE_ROOT / "TOP20_QE_MANIFEST.csv"

QE_BIN = Path("/home/hk/software/qe-7.5/bin/pw.x")

print("=" * 78)
print("HYDROMATAI — PHASE 15 — GLOBAL H2 → QE")
print("=" * 78)

errors = []
rows = []

# ------------------------------------------------------------------
# 1. Projet
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("1. PROJET")
print("=" * 78)

if not (ROOT / "src/hydromatai").exists():
    print("[FAIL] Projet HydroMatAI introuvable")
    sys.exit(1)

print("[OK] Projet HydroMatAI")

# ------------------------------------------------------------------
# 2. Ranking TOP20
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. RANKING GLOBAL H2 — TOP20")
print("=" * 78)

if not RANKING.exists():
    print(f"[FAIL] Ranking absent : {RANKING}")
    errors.append("ranking absent")
else:
    print(f"[OK] {RANKING}")

    with RANKING.open(
        newline="",
        encoding="utf-8",
    ) as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    if len(rows) < 20:
        print(f"[FAIL] Seulement {len(rows)} candidats")
        errors.append("TOP20 incomplet")
    else:
        rows = rows[:20]
        print("[OK] TOP20 sélectionné")

# ------------------------------------------------------------------
# 3. Préparation répertoires
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("3. ARBORESCENCE QE")
print("=" * 78)

TOP20_ROOT.mkdir(parents=True, exist_ok=True)
pseudo_dir = TOP20_ROOT / "pseudo"
pseudo_dir.mkdir(parents=True, exist_ok=True)

print(f"[OK] {TOP20_ROOT}")
print(f"[OK] {pseudo_dir}")

# ------------------------------------------------------------------
# 4. Pseudopotentiels disponibles
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("4. PSEUDOPOTENTIELS")
print("=" * 78)

qe_pseudo_candidates = [
    Path("/home/hk/software/qe-7.5/pseudo"),
    pseudo_dir,
]

available_upf = {}

for directory in qe_pseudo_candidates:
    if not directory.exists():
        continue

    for upf in directory.glob("*.UPF"):
        available_upf[upf.name] = upf

print(f"[OK] UPF détectés : {len(available_upf)}")

for name, path in sorted(available_upf.items()):
    print(f"  - {name} <- {path}")

# ------------------------------------------------------------------
# 5. Structures
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("5. VALIDATION DES STRUCTURES")
print("=" * 78)

prepared = []

for rank, row in enumerate(rows, start=1):

    name = row.get("name", "").strip()
    cif_value = row.get("cif", "").strip()

    if not name:
        print(f"[FAIL] #{rank}: nom absent")
        errors.append(f"candidat {rank}: nom absent")
        continue

    print(f"\n#{rank:02d} {name}")

    # Chercher le CIF
    candidates = []

    if cif_value:
        raw = Path(cif_value)

        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend([
                ROOT / raw,
                ROOT / "structures" / raw,
                ROOT / "MOF_Library" / raw,
            ])

    candidates.extend([
        ROOT / "structures" / f"{name}.cif",
        ROOT / "MOF_Library" / f"{name}.cif",
        ROOT / "MOF_Library" / name / f"{name}.cif",
    ])

    cif = next(
        (p for p in candidates if p.exists()),
        None,
    )

    if cif is None:
        print("[WARN] CIF non trouvé localement")
        prepared.append({
            "rank": rank,
            "name": name,
            "score": row.get("score", ""),
            "status": "WAITING_STRUCTURE",
            "cif": cif_value,
            "input": "",
            "missing_pseudo": "",
        })
        continue

    print(f"[OK] CIF : {cif}")

    try:
        text = cif.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        print(f"[FAIL] Lecture CIF : {exc}")
        errors.append(f"{name}: lecture CIF")
        continue

    if "data_" not in text and "_cell_length_" not in text:
        print("[FAIL] CIF invalide ou non reconnaissable")
        errors.append(f"{name}: CIF invalide")
        continue

    print("[OK] CIF reconnaissable")

    # Détection simple des éléments depuis _atom_site_type_symbol
    elements = set()

    lines = text.splitlines()

    headers = []
    in_loop = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.lower() == "loop_":
            in_loop = True
            headers = []
            continue

        if in_loop and stripped.startswith("_"):
            headers.append(stripped.split()[0])
            continue

        if in_loop and stripped and not stripped.startswith("_"):
            if headers and "_atom_site_type_symbol" in headers:
                try:
                    idx = headers.index("_atom_site_type_symbol")
                    parts = stripped.split()

                    if len(parts) > idx:
                        symbol = parts[idx]
                        symbol = symbol.strip("'\"")
                        symbol = "".join(
                            c for c in symbol
                            if c.isalpha()
                        )

                        if symbol:
                            elements.add(
                                symbol[0].upper() + symbol[1:].lower()
                            )
                except Exception:
                    pass

    print(
        "[OK] Éléments détectés : "
        + (", ".join(sorted(elements)) if elements else "non déterminés")
    )

    # Vérification pseudo par correspondance de symbole
    missing = []

    for element in sorted(elements):
        matches = [
            filename
            for filename in available_upf
            if filename.lower().startswith(
                element.lower() + "."
            )
        ]

        if not matches:
            missing.append(element)

    if missing:
        print(
            "[WAIT] Pseudopotentiels manquants : "
            + ", ".join(missing)
        )

        prepared.append({
            "rank": rank,
            "name": name,
            "score": row.get("score", ""),
            "status": "WAITING_PSEUDO",
            "cif": str(cif),
            "input": "",
            "missing_pseudo": ";".join(missing),
        })
        continue

    # ------------------------------------------------------------------
    # Création dossier candidat
    # ------------------------------------------------------------------
    candidate_dir = (
        TOP20_ROOT /
        f"{rank:04d}_{name}"
    )

    candidate_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    local_cif = candidate_dir / f"{name}.cif"

    if not local_cif.exists():
        shutil.copy2(cif, local_cif)

    # ------------------------------------------------------------------
    # Génération input QE minimal
    # ------------------------------------------------------------------
    input_file = candidate_dir / "pw.scf.in"

    pseudo_lines = []
    for element in sorted(elements):
        matches = [
            filename
            for filename in available_upf
            if filename.lower().startswith(
                element.lower() + "."
            )
        ]

        pseudo_lines.append(
            f" {element}  1.0  1.0  '{matches[0]}'"
        )

    nat = 0

    for line in lines:
        stripped = line.strip()

        if stripped.lower().startswith(
            "_atom_site_type_symbol"
        ):
            continue

    # Le nombre exact d'atomes sera repris du CIF par les outils
    # de production QE ultérieurs. Ici on ne fabrique pas de nat
    # arbitraire : le fichier reste une préparation contrôlée.
    input_file.write_text(
        f"""&CONTROL
  calculation = 'scf',
  prefix = '{name}',
  pseudo_dir = '{pseudo_dir}',
  outdir = './tmp',
/

&SYSTEM
  ibrav = 0,
  ecutwfc = 60,
  ecutrho = 480,
  occupations = 'fixed',
/

&ELECTRONS
  conv_thr = 1.0d-8,
  electron_maxstep = 200,
  mixing_beta = 0.3,
/

ATOMIC_SPECIES
{chr(10).join(pseudo_lines)}

CELL_PARAMETERS angstrom
! A COMPLETER A PARTIR DU CIF

ATOMIC_POSITIONS angstrom
! A COMPLETER A PARTIR DU CIF

K_POINTS gamma
""",
        encoding="utf-8",
    )

    print("[OK] Pseudopotentiels disponibles")
    print(f"[OK] Préparation : {input_file}")

    prepared.append({
        "rank": rank,
        "name": name,
        "score": row.get("score", ""),
        "status": "QE_INPUT_PREPARED",
        "cif": str(cif),
        "input": str(input_file),
        "missing_pseudo": "",
    })

# ------------------------------------------------------------------
# 6. Manifeste
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("6. MANIFESTE TOP20")
print("=" * 78)

with MANIFEST.open(
    "w",
    newline="",
    encoding="utf-8",
) as fh:
    fields = [
        "rank",
        "name",
        "score",
        "status",
        "cif",
        "input",
        "missing_pseudo",
    ]

    writer = csv.DictWriter(
        fh,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(prepared)

print(f"[OK] Manifeste : {MANIFEST}")

# ------------------------------------------------------------------
# 7. QE disponible
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("7. QUANTUM ESPRESSO")
print("=" * 78)

if QE_BIN.exists():
    print(f"[OK] pw.x : {QE_BIN}")

    # Certains builds de QE ne terminent pas correctement avec -h.
    # On vérifie uniquement que le binaire existe et est exécutable.
    if QE_BIN.is_file() and QE_BIN.stat().st_mode & 0o111:
        print("[OK] Exécutable QE accessible et exécutable")
    else:
        print("[FAIL] pw.x non exécutable")
        errors.append("pw.x non exécutable")
else:
    print("[WARN] pw.x non trouvé à l'emplacement attendu")

# ------------------------------------------------------------------
# 8. Résumé
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("8. RESUME TOP20")
print("=" * 78)

counts = {}

for item in prepared:
    status = item["status"]
    counts[status] = counts.get(status, 0) + 1

for status, count in sorted(counts.items()):
    print(f"{status:<24} : {count}")

# ------------------------------------------------------------------
# 9. Conclusion
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("PHASE 15 — CONCLUSION")
print("=" * 78)

print(f"\nCandidats TOP20 : {len(rows)}")
print(f"Entrées manifeste : {len(prepared)}")
print(f"Erreurs : {len(errors)}")

if errors:
    print("\nBLOQUANTS :")
    for error in errors:
        print(f"  - {error}")

    print("\nSTATUT : PHASE 15 NON VALIDEE")
    sys.exit(1)

print("\n[OK] TOP20 séparé du TOP200")
print("[OK] Ranking H2 utilisé comme source")
print("[OK] Validation des structures effectuée")
print("[OK] Vérification des pseudopotentiels effectuée")
print("[OK] Manifeste QE généré")
print("[OK] Aucun calcul QE lancé")
print("\nSTATUT : PHASE 15 PREPARATION VALIDEE")
print("IMPORTANT : préparation QE uniquement — pas encore de DFT exécutée.")
print("=" * 78)
