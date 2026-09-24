#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path("/home/hk/HydroMatAI")

BASE = ROOT / "calculations/top5_dft/TiFeH2"
WORK = ROOT / "calculations/phase78_55_convergence/TiFeH2"

QE = Path("/home/hk/software/qe-7.5/bin/pw.x")
TEMPLATE = BASE / "TiFeH2_scf_run.in"

ECUT = 140
KX = 7
KY = 7
KZ = 7

# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------

print("=" * 78)
print("PHASE 78.55 — CALCUL 140 Ry / 7×7×7")
print("=" * 78)
print("[INFO] Calcul DFT réel")
print("[INFO] ecutwfc = 140 Ry")
print("[INFO] K_POINTS = 7×7×7")
print("[INFO] shift = 0 0 0")
print("[INFO] Physique inchangée")
print("[INFO] Résultats précédents non modifiés")
print()

# ----------------------------------------------------------------------
# 1. Vérifications
# ----------------------------------------------------------------------

if not QE.exists():
    print(f"[ERROR] pw.x introuvable : {QE}")
    sys.exit(1)

if not TEMPLATE.exists():
    print(f"[ERROR] Template introuvable : {TEMPLATE}")
    sys.exit(1)

WORK.mkdir(parents=True, exist_ok=True)

print("===== 1. VÉRIFICATIONS =====")
print(f"[OK] pw.x      : {QE}")
print(f"[OK] template   : {TEMPLATE}")
print(f"[OK] workdir    : {WORK}")
print()

# ----------------------------------------------------------------------
# 2. Lecture du template
# ----------------------------------------------------------------------

text = TEMPLATE.read_text()

# Vérification des paramètres physiques conservés

def get_value(pattern, label):
    m = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )

    if not m:
        print(
            f"[ERROR] Paramètre introuvable : {label}"
        )
        sys.exit(1)

    return m.group(1).strip()


degauss = get_value(
    r"^\s*degauss\s*=\s*([0-9.+\-eEdD]+)",
    "degauss"
)

smearing = get_value(
    r"^\s*smearing\s*=\s*['\"]([^'\"]+)['\"]",
    "smearing"
)

occupations = get_value(
    r"^\s*occupations\s*=\s*['\"]([^'\"]+)['\"]",
    "occupations"
)

nspin = get_value(
    r"^\s*nspin\s*=\s*([0-9]+)",
    "nspin"
)

pseudo_dir = get_value(
    r"^\s*pseudo_dir\s*=\s*['\"]([^'\"]+)['\"]",
    "pseudo_dir"
)

print("===== 2. PROTOCOLE PHYSIQUE =====")
print(f"ecutwfc     = {ECUT} Ry")
print(f"degauss     = {degauss} Ry")
print(f"smearing    = {smearing}")
print(f"occupations = {occupations}")
print(f"nspin       = {nspin}")
print(f"pseudo_dir  = {pseudo_dir}")
print()

# ----------------------------------------------------------------------
# 3. Modification contrôlée de l'input
# ----------------------------------------------------------------------

def replace_or_fail(
    source,
    pattern,
    replacement,
    label
):

    result = re.sub(
        pattern,
        replacement,
        source,
        count=1,
        flags=re.MULTILINE
    )

    if result == source:
        print(
            f"[ERROR] Impossible de modifier {label}"
        )
        sys.exit(1)

    return result


# ecutwfc = 140 Ry
text = replace_or_fail(
    text,
    r"^\s*ecutwfc\s*=\s*[-+0-9.eE]+\s*,?",
    f"    ecutwfc = {ECUT},",
    "ecutwfc"
)

# K_POINTS = 7x7x7
text = replace_or_fail(
    text,
    r"K_POINTS\s+automatic\s*\n\s*"
    r"\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+",
    f"K_POINTS automatic\n"
    f" {KX} {KY} {KZ} 0 0 0",
    "K_POINTS"
)

# Prefix isolé pour cette série
text = re.sub(
    r"prefix\s*=\s*['\"][^'\"]+['\"]",
    "prefix = 'TiFeH2_conv'",
    text,
    count=1,
    flags=re.IGNORECASE
)

# ----------------------------------------------------------------------
# 4. Écriture
# ----------------------------------------------------------------------

inp = WORK / "ecut140_k777.in"
out = WORK / "ecut140_k777.out"

inp.write_text(text)

print("===== 3. INPUT GÉNÉRÉ =====")
print(f"[IN ] {inp}")
print(f"[OUT] {out}")
print()

# Vérification finale des paramètres dans l'input

generated = inp.read_text()

ecut_check = re.search(
    r"^\s*ecutwfc\s*=\s*([-+0-9.eE]+)",
    generated,
    flags=re.IGNORECASE | re.MULTILINE
)

k_check = re.search(
    r"K_POINTS\s+automatic\s*\n\s*"
    r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
    generated,
    flags=re.IGNORECASE
)

if not ecut_check:
    print("[ERROR] Vérification ecutwfc impossible")
    sys.exit(1)

if not k_check:
    print("[ERROR] Vérification K_POINTS impossible")
    sys.exit(1)

ecut_value = float(ecut_check.group(1))

kx2, ky2, kz2, sx, sy, sz = map(
    int,
    k_check.groups()
)

print(
    f"[CHECK] ecutwfc = {ecut_value:g} Ry"
)

print(
    f"[CHECK] K_POINTS = "
    f"{kx2} {ky2} {kz2} "
    f"{sx} {sy} {sz}"
)

if ecut_value != ECUT:
    print("[ERROR] ecutwfc incorrect")
    sys.exit(1)

if (kx2, ky2, kz2) != (KX, KY, KZ):
    print("[ERROR] grille k incorrecte")
    sys.exit(1)

if (sx, sy, sz) != (0, 0, 0):
    print("[ERROR] shift incorrect")
    sys.exit(1)

print("[OK] Input contrôlé")
print()

# ----------------------------------------------------------------------
# 5. Calcul QE
# ----------------------------------------------------------------------

print("=" * 78)
print("===== 4. EXÉCUTION QUANTUM ESPRESSO =====")
print("=" * 78)
print()

print(
    "[RUN] "
    f"{QE} -in {inp}"
)

with out.open("w") as fout:

    process = subprocess.run(
        [
            str(QE),
            "-in",
            str(inp)
        ],
        stdout=fout,
        stderr=subprocess.STDOUT,
        cwd=str(WORK)
    )

return_code = process.returncode

# ----------------------------------------------------------------------
# 6. Analyse du résultat
# ----------------------------------------------------------------------

data = out.read_text(
    errors="ignore"
)

job_done = (
    "JOB DONE." in data
)

energies = re.findall(
    r"!\s+total energy\s+=\s+"
    r"([-+0-9.eEdD]+)\s+Ry",
    data,
    flags=re.IGNORECASE
)

fermis = re.findall(
    r"the Fermi energy is\s+"
    r"([-+0-9.eEdD]+)\s+ev",
    data,
    flags=re.IGNORECASE
)

energy = None
fermi = None

if energies:
    energy = float(
        energies[-1]
        .replace("D", "E")
        .replace("d", "e")
    )

if fermis:
    fermi = float(
        fermis[-1]
        .replace("D", "E")
        .replace("d", "e")
    )

print()
print("=" * 78)
print("===== 5. RÉSULTAT =====")
print("=" * 78)
print()

print(
    f"Return code : {return_code}"
)

print(
    f"JOB DONE    : {job_done}"
)

if energy is not None:

    print(
        f"Energy      : "
        f"{energy:.8f} Ry"
    )

else:

    print(
        "Energy      : NON DÉTECTÉE"
    )

if fermi is not None:

    print(
        f"Fermi       : "
        f"{fermi:.4f} eV"
    )

else:

    print(
        "Fermi       : NON DÉTECTÉ"
    )

# ----------------------------------------------------------------------
# 7. Contrôle minimal de convergence QE
# ----------------------------------------------------------------------

print()
print("===== 6. CONTRÔLES =====")

if return_code == 0:
    print("[OK] pw.x return code = 0")
else:
    print(
        f"[WARN] pw.x return code = "
        f"{return_code}"
    )

if job_done:
    print("[OK] JOB DONE détecté")
else:
    print("[WARN] JOB DONE absent")

if energy is not None:
    print("[OK] Énergie finale détectée")
else:
    print("[WARN] Énergie finale absente")

if fermi is not None:
    print("[OK] Fermi détecté")
else:
    print("[WARN] Fermi absent")

# ----------------------------------------------------------------------
# 8. Résumé final
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.55 TERMINÉE")
print("=" * 78)

print(
    f"[RESULT] 140 Ry / 7×7×7"
)

if energy is not None:
    print(
        f"[RESULT] Energy = "
        f"{energy:.8f} Ry"
    )

if fermi is not None:
    print(
        f"[RESULT] Fermi = "
        f"{fermi:.4f} eV"
    )

print(
    f"[RESULT] JOB DONE = {job_done}"
)

print(
    f"[OUT] {out}"
)

print("=" * 78)

# Échec explicite si le calcul n'est pas terminé
if return_code != 0 or not job_done:
    sys.exit(2)

