from hydromatai.aida.scientific_status import (
    NumericalEvidence,
    NumericalStatus,
    ScientificStatus,
    evaluate_scientific_status,
)


def stable_evidence():
    return NumericalEvidence(
        scf_converged=10,
        scf_total=10,
        cutoff_status=NumericalStatus.ESTABLISHED,
        kpoints_status=NumericalStatus.ESTABLISHED,
        smearing_status=NumericalStatus.ESTABLISHED,
        electronic_outputs_available=True,
    )


def unstable_evidence():
    return NumericalEvidence(
        scf_converged=10,
        scf_total=10,
        cutoff_status=NumericalStatus.NOT_ESTABLISHED,
        kpoints_status=NumericalStatus.NOT_ESTABLISHED,
        smearing_status=NumericalStatus.NOT_ESTABLISHED,
        electronic_outputs_available=True,
    )


def insufficient_evidence():
    return NumericalEvidence(
        scf_converged=10,
        scf_total=10,
        cutoff_status=NumericalStatus.INSUFFICIENT,
        kpoints_status=NumericalStatus.NOT_ESTABLISHED,
        smearing_status=NumericalStatus.NOT_ESTABLISHED,
        electronic_outputs_available=False,
    )


def test_stable_series():
    result = evaluate_scientific_status(stable_evidence())

    assert result.status == (
        ScientificStatus.NUMERICAL_STABILITY_ESTABLISHED
    )
    assert result.numerical_stability == NumericalStatus.ESTABLISHED


def test_unstable_series():
    result = evaluate_scientific_status(unstable_evidence())

    assert result.status == ScientificStatus.NOT_ESTABLISHED
    assert result.numerical_stability == NumericalStatus.NOT_ESTABLISHED


def test_insufficient_series():
    result = evaluate_scientific_status(insufficient_evidence())

    assert result.status == ScientificStatus.INSUFFICIENT_EVIDENCE
    assert result.numerical_stability == NumericalStatus.INSUFFICIENT


def test_scf_convergence_alone_is_not_validation():
    evidence = NumericalEvidence(
        scf_converged=10,
        scf_total=10,
        cutoff_status=NumericalStatus.NOT_ESTABLISHED,
        kpoints_status=NumericalStatus.NOT_ESTABLISHED,
        smearing_status=NumericalStatus.NOT_ESTABLISHED,
        electronic_outputs_available=True,
    )

    result = evaluate_scientific_status(evidence)

    assert result.status != ScientificStatus.NUMERICAL_STABILITY_ESTABLISHED


def test_electronic_outputs_do_not_override_instability():
    evidence = unstable_evidence()

    result = evaluate_scientific_status(evidence)

    assert result.status == ScientificStatus.NOT_ESTABLISHED
