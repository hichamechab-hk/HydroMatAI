from hydromatai.aida import AIDA, render_report
from hydromatai.aida.real_data import build_tifeh2_numerical_evidence


def test_real_tifeh2_numerical_evidence():
    evidence = build_tifeh2_numerical_evidence()

    assert evidence.scf_total == 16
    assert evidence.scf_converged == 14
    assert evidence.scf_incomplete == 2

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
