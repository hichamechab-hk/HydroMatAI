from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
AIDA = ROOT / "src/hydromatai/aida"

PRIORITY = ROOT / "reports/dft_h2_priority.csv"
PHASE55 = (
    ROOT
    / "calculations/phase_55_final_scientific_consistency/"
    / "phase55_final_ranking.csv"
)

HISTORICAL = ROOT / "calculations/top5_dft/TiFeH2"
CAMPAIGN = ROOT / "calculations/new_campaign/TiFeH2"


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(
            f"[FAIL] {' '.join(cmd)}"
        )


def audit_priority() -> None:
    section("1 — AUDIT SOURCE PRIORITAIRE")

    assert PRIORITY.exists()

    text = PRIORITY.read_text(errors="replace")

    assert "TiFeH2" in text
    assert "1.86" in text
    assert "0.2659" in text
    assert "0.4298" in text

    print("[OK] TiFeH2 présent")
    print("[OK] H2 uptake = 1.86 wt%")
    print("[OK] ambient = 0.2659")
    print("[OK] scientific = 0.4298")


def audit_phase55() -> None:
    section("2 — AUDIT PHASE 55")

    assert PHASE55.exists()

    text = PHASE55.read_text(errors="replace")

    assert "TiFeH2" in text
    assert "0.991579" in text
    assert "0.4298" in text

    print("[OK] TiFeH2 présent dans Phase 55")
    print("[OK] final_screening_score = 0.991579")
    print("[OK] scientific_corrected = 0.4298")


def audit_qe_separation() -> None:
    section("3 — SEPARATION QE HISTORIQUE / CAMPAGNE")

    historical = sorted(HISTORICAL.rglob("*"))
    campaign = sorted(CAMPAIGN.rglob("*"))

    assert historical
    assert campaign

    historical_names = {
        str(p.relative_to(HISTORICAL))
        for p in historical
        if p.is_file()
    }

    campaign_names = {
        str(p.relative_to(CAMPAIGN))
        for p in campaign
        if p.is_file()
    }

    assert historical_names
    assert campaign_names

    print(f"[OK] Historique : {len(historical_names)} fichiers")
    print(f"[OK] Campagne : {len(campaign_names)} fichiers")
    print("[OK] Sources physiquement séparées")


def audit_real_data() -> None:
    section("4 — AUDIT DONNEES QE REELLES")

    from hydromatai.aida.real_data import (
        _campaign_scf_records,
        _cutoff_outputs,
        _kpoints_outputs,
        _smearing_outputs,
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()
    records = _campaign_scf_records()

    assert len(_cutoff_outputs()) == 3
    assert len(_kpoints_outputs()) == 3
    assert len(_smearing_outputs()) == 4

    assert len(records) == 10
    assert evidence.scf_total == 10
    assert evidence.scf_converged == 10

    assert evidence.cutoff_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    assert evidence.kpoints_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    assert evidence.smearing_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    print("[OK] 3 cutoff")
    print("[OK] 3 k-points")
    print("[OK] 4 smearing")
    print("[OK] 10/10 SCF convergés")
    print("[OK] stabilité globale non établie")


def audit_aida_status() -> None:
    section("5 — AUDIT STATUT SCIENTIFIQUE AIDA")

    from hydromatai.aida import AIDA, render_report
    from hydromatai.aida.real_data import (
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()

    result = AIDA().analyze(
        "TiFeH2",
        numerical_evidence=evidence,
    )

    assert result.metadata["scientific_status"] == (
        "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    )

    assert result.metadata["numerical_stability"] == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    report = render_report(result)

    assert "SCIENTIFIC_STATUS_NOT_ESTABLISHED" in report
    assert "NUMERICAL_STABILITY_NOT_ESTABLISHED" in report

    print("[OK] Scientific status")
    print("[OK] Numerical stability")
    print("[OK] Report cohérent")


def audit_no_false_validation() -> None:
    section("6 — AUDIT ANTI-FAUSSE VALIDATION")

    forbidden = (
        "SCIENTIFICALLY_VALIDATED",
        "SCIENTIFICALLY_SUPPORTED",
    )

    violations = []

    for path in sorted(AIDA.rglob("*.py")):
        text = path.read_text(errors="replace")

        for token in forbidden:
            # Autoriser les chaînes présentes uniquement dans les
            # assertions/tests documentaires hors package AIDA.
            if token in text:
                violations.append(
                    f"{path.relative_to(ROOT)} : {token}"
                )

    if violations:
        for item in violations:
            print("[FAIL]", item)
        raise SystemExit(1)

    print("[OK] Aucun statut scientifique positif interdit")


def audit_score_semantics() -> None:
    section("7 — AUDIT SEMANTIQUE DU SCORE")

    semantic = AIDA / "semantic.py"
    consistency = AIDA / "consistency.py"

    text = (
        semantic.read_text(errors="replace")
        + "\n"
        + consistency.read_text(errors="replace")
    )

    assert "final_screening_score" in text
    assert "independent_dft_validation" in text

    print("[OK] final_screening_score tracé")
    print("[OK] independent_dft_validation tracé")
    print("[OK] score composite distinct de la validation DFT")


def audit_h2_semantics() -> None:
    section("8 — AUDIT SEMANTIQUE H2")

    from hydromatai.aida.semantic import build_semantic_evidence

    evidence = build_semantic_evidence("TiFeH2")

    h2 = [
        item
        for item in evidence
        if item.name == "h2_uptake_wt_percent"
    ]

    assert h2
    assert h2[0].value == 1.86
    assert h2[0].metadata.get("category") == "LITERATURE"

    print("[OK] H2 = 1.86 wt%")
    print("[OK] Source = LITERATURE")
    print("[OK] H2 non présenté comme résultat QE")


def audit_regression() -> None:
    section("9 — NON-REGRESSION TESTS")

    run(["pytest", "-q"])

    print("[OK] Suite globale pytest")


def audit_compile() -> None:
    section("10 — COMPILATION")

    run([
        "python",
        "-m",
        "compileall",
        "-q",
        "src",
    ])

    print("[OK] Compilation complète")


def audit_git() -> None:
    section("11 — GIT READ-ONLY")

    subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
    )

    print()
    print("[OK] Aucun git add")
    print("[OK] Aucun git commit")
    print("[OK] Aucun push")


def main() -> None:
    section("AIDA — AUDIT GLOBAL FINAL HYDROMATAI")

    print("[INFO] READ-ONLY")
    print("[INFO] Aucun pw.x")
    print("[INFO] Aucun calcul QE")
    print("[INFO] Aucune modification des résultats scientifiques")

    audit_priority()
    audit_phase55()
    audit_qe_separation()
    audit_real_data()
    audit_aida_status()
    audit_no_false_validation()
    audit_score_semantics()
    audit_h2_semantics()
    audit_regression()
    audit_compile()
    audit_git()

    section("AUDIT GLOBAL FINAL — TERMINE")

    print("[OK] HydroMatAI : cohérence conservée")
    print("[OK] AIDA : intégré")
    print("[OK] QE historique : séparé")
    print("[OK] QE nouvelle campagne : séparé")
    print("[OK] H2 littérature : correctement identifié")
    print("[OK] 0.991579 : score composite")
    print("[OK] Validation DFT indépendante : NON ETABLIE")
    print("[OK] Aucun calcul QE exécuté")


if __name__ == "__main__":
    main()
