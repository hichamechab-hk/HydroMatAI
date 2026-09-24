#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE="/home/hk/software/qe-7.5-scalapack/bin/pw.x"

SOURCE="/home/hk/HydroMatAI/calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in"

ROOT="/home/hk/HydroMatAI/calculations/phase78_75_scalapack_full/TiFeH2"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN="$ROOT/run_$RUN_ID"

MPI_N=16
NPOOL=2
NDIAG=2
SCF_MAX=200

echo "=============================================================================="
echo "PHASE 78.75 — VALIDATION COMPLÈTE TiFeH2 — SCALAPACK"
echo "=============================================================================="
echo
echo "[INFO] MODE = CALCUL SCIENTIFIQUE COMPLET"
echo "[INFO] QE        = $QE"
echo "[INFO] Structure = TiFeH2"
echo "[INFO] ecutwfc  = 140 Ry"
echo "[INFO] ecutrho  = 560 Ry"
echo "[INFO] k-point  = 8x8x8"
echo "[INFO] MPI      = $MPI_N"
echo "[INFO] npool    = $NPOOL"
echo "[INFO] ndiag    = $NDIAG"
echo "[INFO] maxstep  = $SCF_MAX"
echo
echo "[INFO] Fichier source : $SOURCE"
echo "[INFO] Le fichier scientifique source restera INCHANGÉ."
echo

[[ -x "$QE" ]] || {
    echo "[ERREUR] pw.x ScaLAPACK absent ou non exécutable."
    exit 1
}

[[ -f "$SOURCE" ]] || {
    echo "[ERREUR] Input source absent : $SOURCE"
    exit 1
}

mkdir -p "$RUN"

echo "=============================================================================="
echo "===== 1. VÉRIFICATION BUILD ================================================"
echo "=============================================================================="
echo

echo "[SHA256]"
sha256sum "$QE"

echo
echo "[LDD]"
ldd "$QE" | grep -E \
    "scalapack|lapack|blas|mpi|fftw" || true

if ! ldd "$QE" | grep -q 'libscalapack-openmpi'; then
    echo "[ERREUR] ScaLAPACK non détectée dans pw.x."
    exit 1
fi

echo
echo "[OK] Build ScaLAPACK confirmée."

echo "=============================================================================="
echo "===== 2. CRÉATION INPUT ISOLÉ =============================================="
echo "=============================================================================="
echo

cp "$SOURCE" "$RUN/TiFeH2_scalapack.in"

python - "$RUN/TiFeH2_scalapack.in" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()

lines = text.splitlines()

# ------------------------------------------------------------
# 1. Remplacer electron_maxstep s'il existe déjà
# ------------------------------------------------------------
found = False
out = []

for line in lines:
    stripped = line.strip()

    if stripped.lower().startswith("electron_maxstep"):
        out.append(" electron_maxstep = 200,")
        found = True
    else:
        out.append(line)

# ------------------------------------------------------------
# 2. S'il n'existe pas, l'insérer dans &ELECTRONS
# ------------------------------------------------------------
if not found:
    result = []
    in_electrons = False
    inserted = False

    for line in out:
        stripped = line.strip()

        if stripped.upper() == "&ELECTRONS":
            in_electrons = True
            result.append(line)
            continue

        if in_electrons and stripped == "/":
            result.append(" electron_maxstep = 200,")
            result.append(line)
            inserted = True
            in_electrons = False
            continue

        result.append(line)

    if not inserted:
        raise SystemExit(
            "[ERREUR] Bloc &ELECTRONS introuvable : "
            "impossible de définir electron_maxstep."
        )

    out = result

path.write_text("\n".join(out) + "\n")

print("[OK] electron_maxstep = 200 configuré dans l'input isolé.")
PY

echo
echo "[INPUT ISOLÉ]"
echo "$RUN/TiFeH2_scalapack.in"

echo
echo "[CONTRÔLE electron_maxstep]"
grep -n -i "electron_maxstep" "$RUN/TiFeH2_scalapack.in"

echo "=============================================================================="
echo "===== 3. CONTRÔLE SCIENTIFIQUE INPUT ======================================="
echo "=============================================================================="
echo

echo "[PARAMÈTRES SOURCE]"
grep -Ei \
    "ecutwfc|ecutrho|occupations|smearing|degauss|nspin|nat|ntyp|prefix|outdir" \
    "$SOURCE" || true

echo
echo "[PARAMÈTRES INPUT ISOLÉ]"
grep -Ei \
    "ecutwfc|ecutrho|occupations|smearing|degauss|nspin|nat|ntyp|prefix|outdir|electron_maxstep" \
    "$RUN/TiFeH2_scalapack.in" || true

echo
echo "[OK] Source conservée intacte."
echo

echo "=============================================================================="
echo "===== 4. LANCEMENT CALCUL COMPLET =========================================="
echo "=============================================================================="
echo

cd "$RUN"

START="$(date +%s)"

mpirun \
    --allow-run-as-root \
    -np "$MPI_N" \
    "$QE" \
    -npool "$NPOOL" \
    -ndiag "$NDIAG" \
    -in TiFeH2_scalapack.in \
    > TiFeH2_scalapack.out 2>&1

END="$(date +%s)"
ELAPSED=$((END - START))

echo
echo "[OK] Calcul terminé."
echo "[INFO] Temps shell = ${ELAPSED} s"

echo "=============================================================================="
echo "===== 5. STATUT QE =========================================================="
echo "=============================================================================="
echo

if grep -q "JOB DONE" TiFeH2_scalapack.out; then
    echo "[OK] JOB DONE détecté."
else
    echo "[ATTENTION] JOB DONE absent."
fi

echo
echo "[SCF ITERATIONS]"
grep -c "iteration #" TiFeH2_scalapack.out || true

echo
echo "[CONVERGENCE]"
grep -E \
    "convergence has been achieved|convergence NOT achieved|convergence has not been achieved" \
    TiFeH2_scalapack.out | tail -5 || true

echo
echo "[c_bands WARNINGS]"
WARNINGS="$(grep -c "c_bands:.*eigenvalues not converged" \
    TiFeH2_scalapack.out || true)"
echo "$WARNINGS"

echo "=============================================================================="
echo "===== 6. ÉNERGIE ============================================================"
echo "=============================================================================="
echo

grep -E "!.*total energy" TiFeH2_scalapack.out | tail -5 || true

echo "=============================================================================="
echo "===== 7. FERMI =============================================================="
echo "=============================================================================="
echo

grep -E \
    "the Fermi energy is|highest occupied level" \
    TiFeH2_scalapack.out | tail -5 || true

echo "=============================================================================="
echo "===== 8. TIMINGS ============================================================"
echo "=============================================================================="
echo

grep -E \
    "PWSCF        :|c_bands|cegterg|cdiaghg|h_psi|fftw" \
    TiFeH2_scalapack.out | tail -30 || true

echo "=============================================================================="
echo "===== 9. DISTRIBUTION MPI ==================================================="
echo "=============================================================================="
echo

grep -E \
    "Parallel version|MPI processes distributed|proc/nbgrp/npool/nimage|number of Kohn-Sham states|number of k points" \
    TiFeH2_scalapack.out | head -25 || true

echo "=============================================================================="
echo "===== 10. RÉSUMÉ FINAL ======================================================="
echo "=============================================================================="
echo

python - "$RUN/TiFeH2_scalapack.out" "$ELAPSED" "$WARNINGS" <<'PY'
import sys
from pathlib import Path

out = Path(sys.argv[1])
elapsed = int(sys.argv[2])
warnings = int(sys.argv[3])

text = out.read_text(errors="replace")

iterations = text.count("iteration #")

energies = [
    line.strip()
    for line in text.splitlines()
    if "!    total energy" in line
]

fermi = [
    line.strip()
    for line in text.splitlines()
    if "the Fermi energy is" in line
]

job_done = "JOB DONE" in text
converged = "convergence has been achieved" in text

print(f"SCF iterations   : {iterations}")
print(f"Elapsed shell    : {elapsed} s")
print(f"c_bands warnings : {warnings}")
print(f"JOB DONE         : {'YES' if job_done else 'NO'}")
print(f"SCF convergence  : {'YES' if converged else 'CHECK'}")

if energies:
    print(f"Final energy     : {energies[-1]}")
else:
    print("Final energy     : NOT FOUND")

if fermi:
    print(f"Final Fermi      : {fermi[-1]}")
else:
    print("Final Fermi      : NOT FOUND")

summary = f"""PHASE 78.75 — TiFeH2 — FULL SCALAPACK VALIDATION
====================================================

BUILD
-----
/home/hk/software/qe-7.5-scalapack/bin/pw.x

PROTOCOL
--------
ecutwfc : 140 Ry
ecutrho : 560 Ry
k-point : 8x8x8
MPI     : 16
npool   : 2
ndiag   : 2
maxstep : 200

RESULT
------
SCF iterations   : {iterations}
Elapsed shell    : {elapsed} s
c_bands warnings : {warnings}
JOB DONE         : {'YES' if job_done else 'NO'}
SCF convergence  : {'YES' if converged else 'CHECK'}

FINAL ENERGY
------------
{energies[-1] if energies else 'NOT FOUND'}

FINAL FERMI
-----------
{fermi[-1] if fermi else 'NOT FOUND'}

OUTPUT
------
{out}
"""

(out.parent / "PHASE_78_75_SUMMARY.txt").write_text(summary)

print()
print(f"[OK] Rapport : {out.parent / 'PHASE_78_75_SUMMARY.txt'}")
PY

echo
echo "=============================================================================="
echo "PHASE 78.75 TERMINÉE"
echo "=============================================================================="
echo
echo "[OK] Source scientifique inchangée."
echo "[OK] Calcul isolé :"
echo "     $RUN"
echo
