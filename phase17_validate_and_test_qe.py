#!/usr/bin/env python3

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QE_BIN = Path("/home/hk/software/qe-7.5/bin/pw.x")

QE_ROOT = ROOT / "calculations/global_screening/qe/TOP20"
MANIFEST = QE_ROOT / "TOP20_QE_MANIFEST.csv"
TOP1_DIR = QE_ROOT / "0001_hMOF-5064089"
TOP1_INPUT = TOP1_DIR / "pw.scf.in"
TOP1_TMP = TOP1_DIR / "tmp"
TOP1_OUTPUT = TOP1_DIR / "pw.scf.out"


def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)


def check_binary() -> None:
    print("[1/7] Vérification Quantum ESPRESSO...")

    if not QE_BIN.exists():
        fail(f"pw.x absent : {QE_BIN}")

    if not os.access(QE_BIN, os.X_OK):
        fail(f"pw.x non exécutable : {QE_BIN}")

    print(f"[OK] pw.x : {QE_BIN}")


def check_manifest() -> list[dict[str, str]]:
    print("[2/7] Vérification du manifeste...")

    if not MANIFEST.exists():
        fail(f"Manifeste absent : {MANIFEST}")

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 20:
        fail(f"Manifeste incomplet : {len(rows)}/20")

    for row in rows:
        if row.get("status") != "QE_INPUT_READY":
            fail(
                f"Entrée non prête : "
                f"{row.get('name')} -> {row.get('status')}"
            )

    print("[OK] 20/20 entrées QE_READY")
    return rows


def validate_input() -> str:
    print("[3/7] Validation du input TOP1...")

    if not TOP1_INPUT.exists():
        fail(f"Input TOP1 absent : {TOP1_INPUT}")

    text = TOP1_INPUT.read_text(encoding="utf-8")

    required = [
        "&CONTROL",
        "&SYSTEM",
        "&ELECTRONS",
        "ATOMIC_SPECIES",
        "CELL_PARAMETERS",
        "ATOMIC_POSITIONS",
        "K_POINTS gamma",
        "calculation = 'scf'",
        "ibrav = 0",
        "ecutwfc = 60.0",
        "ecutrho = 480.0",
    ]

    for item in required:
        if item not in text:
            fail(f"Bloc/paramètre absent : {item}")

    match_nat = re.search(r"\bnat\s*=\s*(\d+)", text)
    match_ntyp = re.search(r"\bntyp\s*=\s*(\d+)", text)

    if not match_nat or not match_ntyp:
        fail("nat/ntyp introuvables")

    nat = int(match_nat.group(1))
    ntyp = int(match_ntyp.group(1))

    pos_match = re.search(
        r"ATOMIC_POSITIONS\s+[^\n]+\n(.*?)(?:\n\s*K_POINTS|\Z)",
        text,
        re.S,
    )

    if not pos_match:
        fail("ATOMIC_POSITIONS introuvable")

    positions = [
        line.strip()
        for line in pos_match.group(1).splitlines()
        if line.strip()
    ]

    if len(positions) != nat:
        fail(
            f"Nombre de positions incorrect : "
            f"{len(positions)} au lieu de {nat}"
        )

    species_match = re.search(
        r"ATOMIC_SPECIES\s*\n(.*?)(?:\n\s*CELL_PARAMETERS|\Z)",
        text,
        re.S,
    )

    if not species_match:
        fail("ATOMIC_SPECIES introuvable")

    species = [
        line.strip()
        for line in species_match.group(1).splitlines()
        if line.strip()
    ]

    if len(species) != ntyp:
        fail(
            f"Nombre d'espèces incorrect : "
            f"{len(species)} au lieu de {ntyp}"
        )

    print(f"[OK] Input valide : nat={nat}, ntyp={ntyp}")
    return text


def validate_pseudopotentials(text: str) -> None:
    print("[4/7] Vérification des pseudopotentiels...")

    pseudo_dir_match = re.search(
        r"pseudo_dir\s*=\s*'([^']+)'",
        text,
    )

    if not pseudo_dir_match:
        fail("pseudo_dir absent")

    pseudo_dir = Path(pseudo_dir_match.group(1))

    if not pseudo_dir.is_absolute():
        pseudo_dir = (TOP1_DIR / pseudo_dir).resolve()

    if not pseudo_dir.exists():
        fail(f"pseudo_dir absent : {pseudo_dir}")

    species_match = re.search(
        r"ATOMIC_SPECIES\s*\n(.*?)(?:\n\s*CELL_PARAMETERS|\Z)",
        text,
        re.S,
    )

    species = [
        line.strip().split()
        for line in species_match.group(1).splitlines()
        if line.strip()
    ]

    missing = []

    for parts in species:
        if len(parts) < 3:
            fail(f"ATOMIC_SPECIES invalide : {' '.join(parts)}")

        pseudo = parts[2]
        pseudo_path = pseudo_dir / pseudo

        if not pseudo_path.exists():
            missing.append(pseudo)

    if missing:
        fail(
            "Pseudopotentiels absents : "
            + ", ".join(sorted(set(missing)))
        )

    print(f"[OK] {len(species)} pseudopotentiels présents")


def prepare_run_directory() -> None:
    print("[5/7] Préparation du calcul TOP1...")

    TOP1_TMP.mkdir(parents=True, exist_ok=True)

    # Nettoyage uniquement des anciens fichiers de sortie
    # générés par ce test, jamais de l'input.
    for filename in ["pw.scf.out", "pw.scf.err"]:
        path = TOP1_DIR / filename
        if path.exists():
            path.unlink()

    print(f"[OK] Répertoire : {TOP1_DIR}")


def run_qe() -> int:
    print("[6/7] Lancement SCF contrôlé TOP1...")
    print()
    print("  Candidat : hMOF-5064089")
    print("  Calcul   : SCF")
    print("  QE       : pw.x")
    print("  TOP20    : aucun autre calcul lancé")
    print()

    cmd = [
        str(QE_BIN),
        "-in",
        str(TOP1_INPUT),
    ]

    output_path = TOP1_OUTPUT
    error_path = TOP1_DIR / "pw.scf.err"

    with output_path.open("w", encoding="utf-8") as out, \
         error_path.open("w", encoding="utf-8") as err:

        try:
            result = subprocess.run(
                cmd,
                cwd=TOP1_DIR,
                stdout=out,
                stderr=err,
                timeout=1800,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print("[ERROR] Timeout QE après 30 minutes")
            return 124

    print(f"[INFO] Code retour pw.x : {result.returncode}")
    return result.returncode


def analyze_output(return_code: int) -> bool:
    print("[7/7] Analyse du résultat QE...")

    if not TOP1_OUTPUT.exists():
        print("[ERROR] Fichier de sortie QE absent")
        return False

    text = TOP1_OUTPUT.read_text(
        encoding="utf-8",
        errors="replace",
    )

    error_text = ""
    error_path = TOP1_DIR / "pw.scf.err"

    if error_path.exists():
        error_text = error_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    if return_code != 0:
        print("[ERROR] pw.x s'est terminé avec une erreur")
        if "Error in routine" in text:
            print("[INFO] Erreur QE détectée dans pw.scf.out")
        return False

    fatal_patterns = [
        "Error in routine",
        "%%%%%%%%%%%%%%",
        "convergence NOT achieved",
        "Maximum CPU time exceeded",
    ]

    for pattern in fatal_patterns:
        if pattern in text or pattern in error_text:
            print(f"[ERROR] Motif QE problématique détecté : {pattern}")
            return False

    converged = (
        "convergence has been achieved" in text
        or "End of self-consistent calculation" in text
    )

    if not converged:
        print("[WARNING] Fin SCF/convergence non confirmée dans la sortie")
        print("[INFO] Le fichier complet est conservé pour diagnostic")
        return False

    energies = re.findall(
        r"!\s+total energy\s+=\s+([-\d.Ee+]+)\s+Ry",
        text,
    )

    print("[OK] SCF terminé")
    print("[OK] Convergence détectée")

    if energies:
        print(f"[OK] Énergie finale : {energies[-1]} Ry")

    return True


def main() -> int:
    print("=" * 78)
    print("PHASE 17 — VALIDATION QE + SCF CONTRÔLÉ TOP1")
    print("=" * 78)
    print()

    check_binary()
    check_manifest()
    text = validate_input()
    validate_pseudopotentials(text)
    prepare_run_directory()

    return_code = run_qe()
    success = analyze_output(return_code)

    print()
    print("=" * 78)
    print("PHASE 17 — CONCLUSION")
    print("=" * 78)
    print()
    print("TOP20 préparé       : 20/20")
    print("TOP1 testé          : hMOF-5064089")
    print(f"Code retour pw.x    : {return_code}")
    print(f"Sortie QE           : {TOP1_OUTPUT}")
    print()

    if success:
        print("[OK] Quantum ESPRESSO opérationnel")
        print("[OK] Input TOP1 accepté")
        print("[OK] SCF TOP1 convergé")
        print("[OK] Aucun autre calcul TOP20 lancé")
        print()
        print("STATUT : PHASE 17 VALIDEE")
        print("Prochaine étape : lancement DFT contrôlé du TOP20.")
        print("=" * 78)
        return 0

    print("[FAIL] Le SCF TOP1 n'est pas validé")
    print("[INFO] Aucun lancement TOP20 ne doit être effectué")
    print()
    print("STATUT : PHASE 17 BLOQUEE — DIAGNOSTIC QE REQUIS")
    print("=" * 78)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
