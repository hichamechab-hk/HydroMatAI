#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path("/home/hk/HydroMatAI")
AIDA_DIR = ROOT / "src/hydromatai/aida"
TEST_DIR = ROOT / "tests/aida"
CAMPAIGN_DIR = ROOT / "calculations/new_campaign/TiFeH2"
HISTORICAL_DIR = ROOT / "calculations/top5_dft/TiFeH2"
BACKUP_DIR = Path("/tmp/aida_phase15_final_backup")

THRESHOLD_RY = 1e-4


def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True)


def backup(path: Path) -> None:
    if not path.exists():
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    target = BACKUP_DIR / path.name
    shutil.copy2(path, target)
    print(f"[BACKUP] {path} -> {target}")


def read_text(path: Path) -> str:
    return path.read_text(errors="replace")


def extract_total_energy(text: str) -> float | None:
    matches = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        flags=re.IGNORECASE,
    )

    if not matches:
        return None

    return float(matches[-1])


def has_scf_convergence(text: str) -> bool:
    lowered = text.lower()

    patterns = (
        "convergence has been achieved",
        "convergence achieved",
        "job done",
    )

    return any(pattern in lowered for pattern in patterns)


def extract_iterations(text: str) -> int | None:
    matches = re.findall(
        r"convergence has been achieved after\s+(\d+)\s+iterations",
        text,
        flags=re.IGNORECASE,
    )

    if matches:
        return int(matches[-1])

    return None


def extract_fermi(text: str) -> float | None:
    patterns = [
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            return float(matches[-1])

    return None


def analyze_out(path: Path) -> dict:
    text = read_text(path)

    return {
        "file": path,
        "energy": extract_total_energy(text),
        "converged": has_scf_convergence(text),
        "iterations": extract_iterations(text),
        "fermi": extract_fermi(text),
    }


def analyze_series(paths: list[Path]) -> dict:
    records = [analyze_out(path) for path in sorted(paths)]

    usable = [record for record in records if record["energy"] is not None]
    energies = [record["energy"] for record in usable]

    if not energies:
        return {
            "records": records,
            "usable": 0,
            "spread": None,
            "status": "INSUFFICIENT_EVIDENCE",
        }

    spread = max(energies) - min(energies)

    status = (
        "ESTABLISHED"
        if spread <= THRESHOLD_RY
        else "NOT_ESTABLISHED"
    )

    return {
        "records": records,
        "usable": len(usable),
        "spread": spread,
        "status": status,
    }


def write_real_data_module() -> None:
    path = AIDA_DIR / "real_data.py"

    content = '''from __future__ import annotations

import re
from pathlib import Path

from .scientific_status import NumericalEvidence, NumericalStatus


PROJECT_ROOT = Path("/home/hk/HydroMatAI")
CAMPAIGN_DIR = PROJECT_ROOT / "calculations/new_campaign/TiFeH2"
HISTORICAL_DIR = PROJECT_ROOT / "calculations/top5_dft/TiFeH2"

THRESHOLD_RY = 1e-4


def _read(path: Path) -> str:
    return path.read_text(errors="replace")


def _energy(text: str) -> float | None:
    values = re.findall(
        r"!\\s+total energy\\s+=\\s+([-+]?\\d+(?:\\.\\d+)?)\\s+Ry",
        text,
        flags=re.IGNORECASE,
    )
    return float(values[-1]) if values else None


def _converged(text: str) -> bool:
    lowered = text.lower()
    return (
        "convergence has been achieved" in lowered
        or "convergence achieved" in lowered
    )


def _series_status(paths: list[Path]) -> NumericalStatus:
    energies = []

    for path in sorted(paths):
        value = _energy(_read(path))
        if value is not None:
            energies.append(value)

    if len(energies) < 2:
        return NumericalStatus.INSUFFICIENT

    spread = max(energies) - min(energies)

    if spread <= THRESHOLD_RY:
        return NumericalStatus.ESTABLISHED

    return NumericalStatus.NOT_ESTABLISHED


def _campaign_outputs() -> list[Path]:
    return sorted(CAMPAIGN_DIR.rglob("*.out"))


def _historical_electronic_outputs_available() -> bool:
    patterns = (
        "*bands*.out",
        "*dos*.out",
        "*nscf*.out",
    )

    return any(
        any(HISTORICAL_DIR.rglob(pattern))
        for pattern in patterns
    )


def build_tifeh2_numerical_evidence() -> NumericalEvidence:
    outputs = _campaign_outputs()

    scf_records = []

    for path in outputs:
        text = _read(path)

        if _energy(text) is not None:
            scf_records.append(
                {
                    "path": path,
                    "converged": _converged(text),
                }
            )

    scf_converged = sum(
        1 for record in scf_records
        if record["converged"]
    )
    scf_total = len(scf_records)

    cutoff = sorted(CAMPAIGN_DIR.rglob("cutoff_*.out"))
    kpoints = sorted(CAMPAIGN_DIR.rglob("kpoints_*.out"))
    smearing = sorted(CAMPAIGN_DIR.rglob("degauss_*.out"))

    return NumericalEvidence(
        scf_converged=scf_converged,
        scf_total=scf_total,
        cutoff_status=_series_status(cutoff),
        kpoints_status=_series_status(kpoints),
        smearing_status=_series_status(smearing),
        electronic_outputs_available=(
            _historical_electronic_outputs_available()
        ),
    )
'''  # noqa: E501

    path.write_text(content)
    ok(f"Module réel créé : {path}")


def write_integration_test() -> None:
    path = TEST_DIR / "test_real_data_integration.py"

    content = '''from hydromatai.aida import AIDA, render_report
from hydromatai.aida.real_data import build_tifeh2_numerical_evidence


def test_tifeh2_real_data_status():
    evidence = build_tifeh2_numerical_evidence()

    assert evidence.scf_total >= 1
    assert evidence.scf_converged == evidence.scf_total

    assert evidence.cutoff_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )
    assert evidence.kpoints_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )
    assert evidence.smearing_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    assert evidence.electronic_outputs_available is True


def test_tifeh2_real_data_aida_report():
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
'''  # noqa: E501

    path.write_text(content)
    ok(f"Test d'intégration créé : {path}")


def phase_d1_audit() -> None:
    banner("PHASE 15.4D-1 — AUDIT READ-ONLY DES DONNEES REELLES")

    if not CAMPAIGN_DIR.exists():
        fail(f"Campagne absente : {CAMPAIGN_DIR}")

    if not HISTORICAL_DIR.exists():
        fail(f"Historique absent : {HISTORICAL_DIR}")

    campaign_outs = sorted(CAMPAIGN_DIR.rglob("*.out"))
    historical_outs = sorted(HISTORICAL_DIR.rglob("*.out"))

    print(f"Campagne OUT : {len(campaign_outs)}")
    print(f"Historique OUT : {len(historical_outs)}")

    if not campaign_outs:
        fail("Aucun OUT dans la nouvelle campagne.")

    ok("Historique et nouvelle campagne détectés séparément")


def phase_d2_build() -> None:
    banner("PHASE 15.4D-2 — CONSTRUCTION NUMERICAL_EVIDENCE")

    write_real_data_module()

    sys.path.insert(0, str(ROOT / "src"))

    from hydromatai.aida.real_data import (
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()

    print("SCF converged :", evidence.scf_converged)
    print("SCF total :", evidence.scf_total)
    print("Cutoff :", evidence.cutoff_status.value)
    print("K-points :", evidence.kpoints_status.value)
    print("Smearing :", evidence.smearing_status.value)
    print(
        "Electronic outputs :",
        evidence.electronic_outputs_available,
    )

    if evidence.scf_total != 10:
        fail(
            "Le nombre de calculs SCF analyzables n'est pas 10. "
            f"Valeur détectée : {evidence.scf_total}"
        )

    if evidence.scf_converged != 10:
        fail(
            "Les 10 calculs SCF attendus ne sont pas tous convergés."
        )

    expected = "NUMERICAL_STABILITY_NOT_ESTABLISHED"

    for name, status in (
        ("cutoff", evidence.cutoff_status.value),
        ("kpoints", evidence.kpoints_status.value),
        ("smearing", evidence.smearing_status.value),
    ):
        if status != expected:
            fail(
                f"Statut inattendu pour {name}: {status}"
            )

    ok("NumericalEvidence réel conforme à l'audit Phase 11/12")


def phase_d3_test_real_data() -> None:
    banner("PHASE 15.4D-3 — TEST AIDA REEL TiFeH2")

    sys.path.insert(0, str(ROOT / "src"))

    from hydromatai.aida import AIDA, render_report
    from hydromatai.aida.real_data import (
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()

    result = AIDA().analyze(
        "TiFeH2",
        numerical_evidence=evidence,
    )

    print("Scientific status :",
          result.metadata["scientific_status"])
    print("Numerical stability :",
          result.metadata["numerical_stability"])

    assert result.metadata["scientific_status"] == (
        "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    )

    assert result.metadata["numerical_stability"] == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    report = render_report(result)
    print()
    print(report)

    assert "SCIENTIFIC_STATUS_NOT_ESTABLISHED" in report
    assert "NUMERICAL_STABILITY_NOT_ESTABLISHED" in report

    ok("AIDA réel TiFeH2 validé")


def phase_e1_api_audit() -> None:
    banner("PHASE 15.4E-1 — AUDIT INTEGRATION API")

    path = AIDA_DIR / "orchestrator.py"
    text = read_text(path)

    required = (
        "numerical_evidence",
        "NumericalEvidence",
        "self.analyzer.analyze",
    )

    for item in required:
        if item not in text:
            fail(f"API AIDA incomplète : {item}")

    ok("API publique conserve numerical_evidence")


def phase_e2_separation_audit() -> None:
    banner("PHASE 15.4E-2 — AUDIT HISTORIQUE / NOUVELLE CAMPAGNE")

    historical = sorted(HISTORICAL_DIR.rglob("*.out"))
    campaign = sorted(CAMPAIGN_DIR.rglob("*.out"))

    print("Historical OUT :", len(historical))
    print("New campaign OUT :", len(campaign))

    if not historical:
        fail("Aucune donnée historique détectée.")

    if not campaign:
        fail("Aucune donnée nouvelle détectée.")

    historical_paths = {str(p) for p in historical}
    campaign_paths = {str(p) for p in campaign}

    if historical_paths & campaign_paths:
        fail("Fusion accidentelle historique/nouvelle campagne.")

    ok("Les deux générations QE restent séparées")


def phase_f1_tests() -> None:
    banner("PHASE 15.4F-1 — TESTS D'INTEGRATION COMPLETS")

    run([sys.executable, "-m", "pytest", "-q", "tests/aida"])

    ok("Tests AIDA complets")


def phase_f2_false_validation_audit() -> None:
    banner("PHASE 15.4F-2 — AUDIT ANTI-FAUSSE-VALIDATION")

    forbidden_positive = (
        "SCIENTIFICALLY_VALIDATED",
        "SCIENTIFICALLY_SUPPORTED",
    )

    source_files = list(AIDA_DIR.glob("*.py"))

    for path in source_files:
        text = read_text(path)

        for token in forbidden_positive:
            if token in text:
                fail(
                    f"Terme de validation positive détecté dans "
                    f"{path}: {token}"
                )

    semantic = read_text(AIDA_DIR / "semantic.py")
    consistency = read_text(AIDA_DIR / "consistency.py")

    if "final_screening_score" not in semantic:
        fail("Trace du final_screening_score absente de semantic.py")

    if "final_screening_score" not in consistency:
        fail("Trace du final_screening_score absente de consistency.py")

    ok("Aucune fausse validation positive détectée")


def phase_g_final_audit() -> None:
    banner("PHASE 15.4G — AUDIT FINAL AIDA")

    required_files = (
        AIDA_DIR / "models.py",
        AIDA_DIR / "analyzer.py",
        AIDA_DIR / "orchestrator.py",
        AIDA_DIR / "report.py",
        AIDA_DIR / "scientific_status.py",
        AIDA_DIR / "real_data.py",
        AIDA_DIR / "semantic.py",
        AIDA_DIR / "consistency.py",
    )

    for path in required_files:
        if not path.exists():
            fail(f"Fichier AIDA manquant : {path}")

    sys.path.insert(0, str(ROOT / "src"))

    from hydromatai.aida.real_data import (
        build_tifeh2_numerical_evidence,
    )

    evidence = build_tifeh2_numerical_evidence()

    assert evidence.scf_converged == 10
    assert evidence.scf_total == 10

    assert evidence.cutoff_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    assert evidence.kpoints_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    assert evidence.smearing_status.value == (
        "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    )

    from hydromatai.aida import AIDA

    result = AIDA().analyze(
        "TiFeH2",
        numerical_evidence=evidence,
    )

    assert result.metadata["scientific_status"] == (
        "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    )

    ok("Audit scientifique final AIDA validé")


def phase_h_cleanup_audit() -> None:
    banner("PHASE 15.4H — AUDIT DE NETTOYAGE")

    print("Aucun git add.")
    print("Aucun git commit.")
    print("Aucune suppression automatique de scripts historiques.")
    print("Les backups sont conservés dans :", BACKUP_DIR)

    ok("Nettoyage destructif désactivé")


def phase_i_final_validation() -> None:
    banner("PHASE 15.4I — VALIDATION FINALE")

    run([
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "src/hydromatai/aida",
    ])

    run([sys.executable, "-m", "pytest", "-q", "tests/aida"])

    print()
    print("===== GIT DIFF STAT =====")
    run(["git", "diff", "--stat"], check=False)

    print()
    print("===== GIT STATUS =====")
    run(["git", "status", "--short"], check=False)

    ok("Validation finale terminée")


def main() -> None:
    banner("PHASE 15.4D → 15.4I — AIDA FINAL INTEGRATION")

    print("READ/WRITE contrôlé")
    print("Aucun pw.x ne sera exécuté.")
    print("Aucun fichier QE ne sera modifié.")
    print("Aucun résultat scientifique ne sera recalculé.")
    print()

    for path in (
        AIDA_DIR / "orchestrator.py",
        AIDA_DIR / "report.py",
        AIDA_DIR / "analyzer.py",
        AIDA_DIR / "scientific_status.py",
    ):
        backup(path)

    phase_d1_audit()
    phase_d2_build()
    phase_d3_test_real_data()

    phase_e1_api_audit()
    phase_e2_separation_audit()

    write_integration_test()

    phase_f1_tests()
    phase_f2_false_validation_audit()

    phase_g_final_audit()
    phase_h_cleanup_audit()
    phase_i_final_validation()

    banner("PHASES 15.4D → 15.4I TERMINEES")
    print("[OK] AIDA intégré aux données réelles TiFeH2")
    print("[OK] Statut numérique conservatif")
    print("[OK] Historique/nouvelle campagne séparés")
    print("[OK] Rapport scientifique intégré")
    print("[OK] Anti-fausse-validation contrôlé")
    print("[OK] Tests et compilation validés")
    print("[OK] Aucun git add / commit exécuté")


if __name__ == "__main__":
    main()
