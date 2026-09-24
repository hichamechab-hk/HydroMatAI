from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")
AIDA = ROOT / "src/hydromatai/aida"
TESTS = ROOT / "tests/aida"
REAL_DATA = AIDA / "real_data.py"

BACKUP = Path("/tmp/aida_phase15_final_backup")


def run(cmd: list[str], title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(
            f"[FAIL] Commande échouée ({result.returncode}) : {' '.join(cmd)}"
        )


def read(path: Path) -> str:
    return path.read_text(errors="replace")


def phase_d3() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4D-3 — VALIDATION DES DONNEES REELLES")
    print("=" * 78)

    from hydromatai.aida.real_data import (
        _campaign_scf_records,
        _cutoff_outputs,
        _kpoints_outputs,
        _smearing_outputs,
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()

    assert len(_cutoff_outputs()) == 3
    assert len(_kpoints_outputs()) == 3
    assert len(_smearing_outputs()) == 4

    records = _campaign_scf_records()

    assert len(records) == 10
    assert sum(r["converged"] for r in records) == 10

    assert evidence.scf_total == 10
    assert evidence.scf_converged == 10

    print("[OK] 3 séries cutoff")
    print("[OK] 3 séries k-points")
    print("[OK] 4 séries smearing")
    print("[OK] 10 calculs SCF principaux")
    print("[OK] 10/10 convergés")
    print("[OK] sorties auxiliaires exclues")

    print()
    print("Statut numérique :")
    print("  cutoff   =", evidence.cutoff_status.value)
    print("  k-points =", evidence.kpoints_status.value)
    print("  smearing =", evidence.smearing_status.value)


def phase_e() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4E — AUDIT API ET SEPARATION DES SOURCES")
    print("=" * 78)

    from hydromatai.aida import AIDA, AIDAAnalyzer, Evidence, Finding
    from hydromatai.aida.data_sources import collect_subject_sources
    from hydromatai.aida.real_data import build_tifeh2_numerical_evidence

    assert AIDA is not None
    assert AIDAAnalyzer is not None
    assert Evidence is not None
    assert Finding is not None

    sources = collect_subject_sources("TiFeH2")

    assert sources["subject"] == "TiFeH2"
    assert sources["priority_report"]["material"] == "TiFeH2"
    assert sources["phase55_ranking"]["material"] == "TiFeH2"

    assert "qe_files" in sources

    qe_files = sources["qe_files"]

    assert "historical_top5_dft" in qe_files
    assert "new_campaign" in qe_files

    historical = qe_files["historical_top5_dft"]
    campaign = qe_files["new_campaign"]

    assert historical
    assert campaign

    historical_paths = {
        str(path)
        for path in historical
    }

    campaign_paths = {
        str(path)
        for path in campaign
    }

    assert historical_paths.isdisjoint(campaign_paths)

    assert any(
        "TiFeH2_relax.out" in path
        for path in historical_paths
    )

    assert any(
        "run_60Ry/TiFeH2_cutoff_60.out" in path
        for path in campaign_paths
    )

    assert any(
        "smearing_tests/degauss_0.001Ry/"
        "TiFeH2_degauss_0.001Ry.out" in path
        for path in campaign_paths
    )

    numerical = build_tifeh2_numerical_evidence()

    result = AIDA().analyze(
        "TiFeH2",
        numerical_evidence=numerical,
    )

    assert result.metadata["scientific_status"] == (
        "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    )

    print("[OK] API AIDA")
    print("[OK] sources historiques détectées")
    print("[OK] nouvelle campagne détectée")
    print("[OK] historique et campagne disjoints")
    print("[OK] statut scientifique correctement propagé")


def create_integration_test() -> None:
    path = TESTS / "test_real_data_integration.py"

    content = '''from hydromatai.aida import AIDA, render_report
from hydromatai.aida.real_data import build_tifeh2_numerical_evidence


def test_real_tifeh2_numerical_evidence():
    evidence = build_tifeh2_numerical_evidence()

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


def test_real_tifeh2_aida_status():
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


def test_real_tifeh2_report():
    evidence = build_tifeh2_numerical_evidence()

    result = AIDA().analyze(
        "TiFeH2",
        numerical_evidence=evidence,
    )

    report = render_report(result)

    assert "SCIENTIFIC_STATUS_NOT_ESTABLISHED" in report
    assert "NUMERICAL_STABILITY_NOT_ESTABLISHED" in report
'''

    path.write_text(content)
    print(f"[OK] Test créé : {path}")


def phase_f() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4F — TESTS D'INTEGRATION")
    print("=" * 78)

    create_integration_test()

    run(
        ["pytest", "-q", "tests/aida"],
        "PHASE 15.4F-1 — PYTEST AIDA",
    )


def phase_g() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4G — AUDIT ANTI-FAUSSE-VALIDATION")
    print("=" * 78)

    forbidden_positive = (
        "SCIENTIFICALLY_VALIDATED",
        "SCIENTIFICALLY_SUPPORTED",
    )

    violations = []

    for path in sorted(AIDA.rglob("*.py")):
        text = read(path)

        for token in forbidden_positive:
            if token in text:
                violations.append(
                    f"{path.relative_to(ROOT)} -> {token}"
                )

    if violations:
        print("[FAIL] Claims scientifiques positifs interdits détectés :")
        for item in violations:
            print("  ", item)
        raise SystemExit(1)

    print("[OK] Aucun SCIENTIFICALLY_VALIDATED")
    print("[OK] Aucun SCIENTIFICALLY_SUPPORTED")

    semantic = AIDA / "semantic.py"
    consistency = AIDA / "consistency.py"

    for path in (semantic, consistency):
        text = read(path)
        assert "final_screening_score" in text

    print("[OK] final_screening_score reste tracé dans les modules attendus")

    real_data = read(REAL_DATA)

    assert "SCIENTIFIC_STATUS_NOT_ESTABLISHED" not in real_data

    print("[OK] real_data.py ne fabrique aucun statut scientifique")


def phase_h() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4H — AUDIT ARCHITECTURE FINALE")
    print("=" * 78)

    scientific_status = AIDA / "scientific_status.py"
    analyzer = AIDA / "analyzer.py"
    orchestrator = AIDA / "orchestrator.py"
    report = AIDA / "report.py"

    for path in (
        scientific_status,
        analyzer,
        orchestrator,
        report,
        REAL_DATA,
    ):
        assert path.exists()
        print("[OK]", path.relative_to(ROOT))

    analyzer_text = read(analyzer)
    orchestrator_text = read(orchestrator)
    report_text = read(report)

    assert "evaluate_scientific_status" in analyzer_text
    assert "numerical_evidence" in analyzer_text

    assert "numerical_evidence" in orchestrator_text

    assert "scientific_status" in report_text
    assert "numerical_stability" in report_text

    print("[OK] scientific_status intégré à analyzer")
    print("[OK] numerical_evidence propagé par orchestrator")
    print("[OK] statut scientifique rendu dans report")


def phase_i() -> None:
    print()
    print("=" * 78)
    print("PHASE 15.4I — VERIFICATION FINALE")
    print("=" * 78)

    run(
        ["python", "-m", "compileall", "-q", "src/hydromatai/aida"],
        "Compilation AIDA",
    )

    run(
        ["pytest", "-q", "tests/aida"],
        "Tests finaux AIDA",
    )

    print()
    print("===== GIT DIFF STATISTIQUE =====")
    subprocess.run(
        ["git", "diff", "--stat", "--",
         "src/hydromatai/aida",
         "tests/aida"],
        cwd=ROOT,
    )

    print()
    print("===== GIT STATUS =====")
    subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
    )

    print()
    print("[OK] Phase 15.4I terminée")
    print("[OK] Aucun git add")
    print("[OK] Aucun git commit")
    print("[OK] Aucun push")


def main() -> None:
    print("=" * 78)
    print("AIDA — PHASE 15.4D-3 → 15.4I")
    print("INTEGRATION FINALE DES DONNEES REELLES")
    print("=" * 78)

    print()
    print("[INFO] Aucun pw.x ne sera exécuté.")
    print("[INFO] Aucun fichier QE ne sera modifié.")
    print("[INFO] Aucun calcul scientifique ne sera lancé.")

    phase_d3()
    phase_e()
    phase_f()
    phase_g()
    phase_h()
    phase_i()

    print()
    print("=" * 78)
    print("PHASES 15.4D-3 → 15.4I : TERMINEES")
    print("=" * 78)


if __name__ == "__main__":
    main()
