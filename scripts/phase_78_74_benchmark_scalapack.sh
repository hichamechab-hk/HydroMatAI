#!/usr/bin/env bash

printf '\033[2J\033[H'

set -euo pipefail

QE_REF="/home/hk/software/qe-7.5/bin/pw.x"
QE_SCAL="/home/hk/software/qe-7.5-scalapack/bin/pw.x"

SOURCE="/home/hk/HydroMatAI/calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888.in"

ROOT="/home/hk/HydroMatAI/calculations/phase78_74_scalapack_benchmark/TiFeH2"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN="$ROOT/run_$RUN_ID"

MPI_N=16
NPOOL=2
NDIAG=2
SCF_STEPS=2

echo "=============================================================================="
echo "PHASE 78.74 — BENCHMARK QE RÉFÉRENCE vs SCALAPACK"
echo "=============================================================================="
echo
echo "[INFO] MODE = BENCHMARK DIAGNOSTIQUE CONTRÔLÉ"
echo "[INFO] QE référence : $QE_REF"
echo "[INFO] QE ScaLAPACK : $QE_SCAL"
echo "[INFO] Structure    : TiFeH2"
echo "[INFO] ecutwfc      : 140 Ry"
echo "[INFO] ecutrho      : 560 Ry"
echo "[INFO] k-points     : 8x8x8"
echo "[INFO] MPI          : $MPI_N"
echo "[INFO] npool        : $NPOOL"
echo "[INFO] ndiag        : $NDIAG"
echo "[INFO] SCF steps    : $SCF_STEPS"
echo
echo "[INFO] Aucun fichier scientifique source ne sera modifié."
echo

for F in "$QE_REF" "$QE_SCAL" "$SOURCE"; do
    if [[ ! -e "$F" ]]; then
        echo "[ERREUR] Fichier absent : $F"
        exit 1
    fi
done

mkdir -p "$RUN"

echo "=============================================================================="
echo "===== 1. IDENTITÉ DES BUILDS ================================================"
echo "=============================================================================="
echo

echo "[REF]"
sha256sum "$QE_REF"

echo
echo "[SCALAPACK]"
sha256sum "$QE_SCAL"

echo
echo "[REF] Vérification ScaLAPACK"
if ldd "$QE_REF" | grep -q 'libscalapack-openmpi'; then
    echo "[ERREUR] La build de référence utilise ScaLAPACK."
    exit 1
else
    echo "[OK] aucune liaison ScaLAPACK."
fi

echo
echo "[SCALAPACK] Vérification ScaLAPACK"
if ldd "$QE_SCAL" | grep -q 'libscalapack-openmpi'; then
    echo "[OK] liaison ScaLAPACK détectée."
else
    echo "[ERREUR] liaison ScaLAPACK absente."
    exit 1
fi

echo "=============================================================================="
echo "===== 2. PRÉPARATION DES INPUTS ISOLÉS ====================================="
echo "=============================================================================="
echo

make_input() {
    local NAME="$1"
    local OUT="$RUN/$NAME"

    mkdir -p "$OUT"

    python - "$SOURCE" "$OUT/$NAME.in" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

text = src.read_text()
lines = text.splitlines()

out = []
found = False
in_control = False

for line in lines:
    stripped = line.strip()

    if stripped.upper() == "&CONTROL":
        in_control = True

    if in_control and stripped.lower().startswith("electron_maxstep"):
        out.append(" electron_maxstep = 2,")
        found = True
    else:
        out.append(line)

    if in_control and stripped == "/":
        in_control = False

if not found:
    raise SystemExit(
        "[ERREUR] electron_maxstep introuvable dans &CONTROL."
    )

dst.write_text("\n".join(out) + "\n")
PY

    echo "[OK] Input : $OUT/$NAME.in" >&2

    printf '%s\n' "$OUT"
}

REF_DIR="$(make_input "REFERENCE")"
SCAL_DIR="$(make_input "SCALAPACK")"

echo "=============================================================================="
echo "===== 3. CONTRÔLE DES INPUTS ================================================"
echo "=============================================================================="
echo

echo "[REFERENCE]"
grep -n -i "electron_maxstep" "$REF_DIR/REFERENCE.in"

echo
echo "[SCALAPACK]"
grep -n -i "electron_maxstep" "$SCAL_DIR/SCALAPACK.in"

echo
echo "[OK] Les deux inputs sont isolés."
echo

echo "=============================================================================="
echo "===== 4. BENCHMARK REFERENCE ================================================"
echo "=============================================================================="
echo

cd "$REF_DIR"

START_REF="$(date +%s)"

mpirun \
    --allow-run-as-root \
    -np "$MPI_N" \
    "$QE_REF" \
    -npool "$NPOOL" \
    -ndiag "$NDIAG" \
    -in REFERENCE.in \
    > REFERENCE.out 2>&1

END_REF="$(date +%s)"
ELAPSED_REF=$((END_REF - START_REF))

echo "[OK] Référence terminée."
echo "[INFO] Temps shell = ${ELAPSED_REF} s"

echo
echo "[INFO] Contrôle sortie :"
grep -E "PWSCF        :|c_bands:.*eigenvalues not converged|!.*total energy" \
    REFERENCE.out | tail -10 || true

echo "=============================================================================="
echo "===== 5. BENCHMARK SCALAPACK ================================================"
echo "=============================================================================="
echo

cd "$SCAL_DIR"

START_SCAL="$(date +%s)"

mpirun \
    --allow-run-as-root \
    -np "$MPI_N" \
    "$QE_SCAL" \
    -npool "$NPOOL" \
    -ndiag "$NDIAG" \
    -in SCALAPACK.in \
    > SCALAPACK.out 2>&1

END_SCAL="$(date +%s)"
ELAPSED_SCAL=$((END_SCAL - START_SCAL))

echo "[OK] ScaLAPACK terminée."
echo "[INFO] Temps shell = ${ELAPSED_SCAL} s"

echo
echo "[INFO] Contrôle sortie :"
grep -E "PWSCF        :|c_bands:.*eigenvalues not converged|!.*total energy" \
    SCALAPACK.out | tail -10 || true

echo "=============================================================================="
echo "===== 6. EXTRACTION DES TIMINGS ============================================"
echo "=============================================================================="
echo

extract_timings() {
    local FILE="$1"
    local LABEL="$2"

    echo
    echo "---------------- $LABEL ----------------"

    echo "[PWSCF]"
    grep -E "PWSCF        :" "$FILE" | tail -1 || true

    echo
    echo "[c_bands]"
    grep -E "c_bands" "$FILE" | tail -1 || true

    echo
    echo "[cegterg]"
    grep -E "cegterg" "$FILE" | tail -1 || true

    echo
    echo "[cdiaghg]"
    grep -E "cdiaghg" "$FILE" | tail -1 || true

    echo
    echo "[h_psi]"
    grep -E "h_psi" "$FILE" | tail -1 || true

    echo
    echo "[fftw]"
    grep -E "fftw" "$FILE" | tail -1 || true

    echo
    echo "[SCF iterations]"
    grep -c "iteration #" "$FILE" || true

    echo
    echo "[c_bands warnings]"
    grep -c "c_bands:.*eigenvalues not converged" "$FILE" || true
}

extract_timings "$REF_DIR/REFERENCE.out" "REFERENCE"
extract_timings "$SCAL_DIR/SCALAPACK.out" "SCALAPACK"

echo "=============================================================================="
echo "===== 7. ÉNERGIES ==========================================================="
echo "=============================================================================="
echo

echo "[REFERENCE]"
grep -E "!.*total energy" "$REF_DIR/REFERENCE.out" | tail -1 || true

echo
echo "[SCALAPACK]"
grep -E "!.*total energy" "$SCAL_DIR/SCALAPACK.out" | tail -1 || true

echo "=============================================================================="
echo "===== 8. DISTRIBUTION MPI ==================================================="
echo "=============================================================================="
echo

echo "[REFERENCE]"
grep -E \
    "Parallel version|MPI processes distributed|proc/nbgrp/npool/nimage|number of Kohn-Sham states|number of k points" \
    "$REF_DIR/REFERENCE.out" | head -20 || true

echo
echo "[SCALAPACK]"
grep -E \
    "Parallel version|MPI processes distributed|proc/nbgrp/npool/nimage|number of Kohn-Sham states|number of k points" \
    "$SCAL_DIR/SCALAPACK.out" | head -20 || true

echo "=============================================================================="
echo "===== 9. COMPARAISON ========================================================"
echo "=============================================================================="
echo

python - "$ELAPSED_REF" "$ELAPSED_SCAL" "$RUN" <<'PY'
import sys
from pathlib import Path

ref = float(sys.argv[1])
scal = float(sys.argv[2])
run = Path(sys.argv[3])

speedup = ref / scal
gain = (ref - scal) / ref * 100.0

print(f"REFERENCE   : {ref:.2f} s")
print(f"SCALAPACK   : {scal:.2f} s")
print(f"SPEEDUP     : {speedup:.3f} x")
print(f"GAIN        : {gain:.2f} %")

if scal < ref:
    print("[RESULTAT] ScaLAPACK plus rapide sur ce benchmark.")
elif scal > ref:
    print("[RESULTAT] Build référence plus rapide sur ce benchmark.")
else:
    print("[RESULTAT] Temps identiques.")

summary = f"""PHASE 78.74 — BENCHMARK QE RÉFÉRENCE vs SCALAPACK
====================================================

PROTOCOLE
---------
Structure : TiFeH2
ecutwfc   : 140 Ry
ecutrho   : 560 Ry
k-points  : 8x8x8
MPI       : 16
npool     : 2
ndiag     : 2
SCF       : 2

REFERENCE
---------
Executable : /home/hk/software/qe-7.5/bin/pw.x
Elapsed     : {ref:.2f} s

SCALAPACK
---------
Executable : /home/hk/software/qe-7.5-scalapack/bin/pw.x
Elapsed     : {scal:.2f} s

COMPARAISON
-----------
Speedup : {speedup:.3f} x
Gain    : {gain:.2f} %

RUN
---
{run}
"""

(run / "SCALAPACK_COMPARISON_SUMMARY.txt").write_text(summary)

print()
print(f"[OK] Résumé : {run}/SCALAPACK_COMPARISON_SUMMARY.txt")
PY

echo
echo "=============================================================================="
echo "===== 10. FICHIERS DE SORTIE ================================================"
echo "=============================================================================="
echo
echo "[REFERENCE]"
echo "  $REF_DIR/REFERENCE.in"
echo "  $REF_DIR/REFERENCE.out"
echo
echo "[SCALAPACK]"
echo "  $SCAL_DIR/SCALAPACK.in"
echo "  $SCAL_DIR/SCALAPACK.out"
echo
echo "[SUMMARY]"
echo "  $RUN/SCALAPACK_COMPARISON_SUMMARY.txt"
echo

echo "=============================================================================="
echo "PHASE 78.74 TERMINÉE"
echo "=============================================================================="
echo
echo "[OK] Aucun fichier scientifique source n'a été modifié."
echo "[OK] Benchmark effectué avec deux builds QE différentes."
echo
