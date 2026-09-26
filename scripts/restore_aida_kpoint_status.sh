#!/usr/bin/env bash

clear

set -euo pipefail

cd /home/hk/HydroMatAI

echo "=============================================================================="
echo "HYDROMATAI — CORRECTION TESTS AIDA TiFeH2"
echo "=============================================================================="
echo
echo "[INFO] 2/3 calculs k-points 140/560 Ry sont terminés."
echo "[INFO] 3x3x3 = COMPLET"
echo "[INFO] 4x4x4 = COMPLET"
echo "[INFO] 5x5x5 = INCOMPLET"
echo "[INFO] Statut attendu = NUMERICAL_STABILITY_NOT_ESTABLISHED"
echo

TEST_FILE="tests/aida/test_real_data_integration.py"

if [ ! -f "$TEST_FILE" ]; then
    echo "[ERREUR] Fichier introuvable : $TEST_FILE"
    exit 1
fi

cp "$TEST_FILE" "${TEST_FILE}.backup_before_status_restore"

python3 - <<'PY'
from pathlib import Path

path = Path("tests/aida/test_real_data_integration.py")
text = path.read_text()

text = text.replace(
    '''assert evidence.kpoints_status.value == (
        "INSUFFICIENT_EVIDENCE"
    )''',
    '''assert evidence.kpoints_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )'''
)

text = text.replace(
    '''assert result.metadata["scientific_status"] == (
        "INSUFFICIENT_EVIDENCE"
    )''',
    '''assert result.metadata["scientific_status"] == (
        "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    )'''
)

text = text.replace(
    '''assert result.metadata["numerical_stability"] == (
        "INSUFFICIENT_EVIDENCE"
    )''',
    '''assert result.metadata["numerical_stability"] == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )'''
)

text = text.replace(
    'assert "INSUFFICIENT_EVIDENCE" in report',
    'assert "SCIENTIFIC_STATUS_NOT_ESTABLISHED" in report'
)

path.write_text(text)

print("[OK] Assertions AIDA corrigées.")
PY

echo
echo "=== TESTS AIDA ==="
pytest -q tests/aida

echo
echo "=== TESTS AIDA + DFT ==="
pytest -q tests/aida tests/dft

echo
echo "=== SUITE COMPLETE ==="
pytest -q

echo
echo "=============================================================================="
echo "VALIDATION TERMINEE — TERMINAL CONSERVE OUVERT"
echo "=============================================================================="
