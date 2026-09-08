from hydromatai.scientific.evaluation import (
    ScientificEvaluation,
    evaluate_result,
    evaluate_results,
)
from hydromatai.scientific.result import ScientificResult


def test_evaluate_result():
    result = ScientificResult(
        material="Material_A",
        stability_score=0.8,
        hydrogen_score=0.6,
        band_gap=2.0,
        optical_classification="absorber",
    )

    evaluation = evaluate_result(result)

    assert isinstance(evaluation, ScientificEvaluation)
    assert evaluation.material == "Material_A"

    expected = (
        0.30 * 0.8
        + 0.20 * 1.0
        + 0.20 * 1.0
        + 0.30 * 0.6
    )

    assert evaluation.score == round(expected, 4)


def test_electronic_unknown_gets_neutral_score():
    result = ScientificResult(
        material="Material_A",
        stability_score=0.8,
        hydrogen_score=0.6,
        band_gap=None,
        optical_classification="absorber",
    )

    evaluation = evaluate_result(result)

    assert evaluation.electronic_score == 0.5


def test_optical_unknown_gets_neutral_score():
    result = ScientificResult(
        material="Material_A",
        stability_score=0.8,
        hydrogen_score=0.6,
        band_gap=2.0,
        optical_classification="unknown",
    )

    evaluation = evaluate_result(result)

    assert evaluation.optical_score == 0.5


def test_scores_are_clamped():
    result = ScientificResult(
        material="Material_A",
        stability_score=2.0,
        hydrogen_score=-1.0,
        band_gap=1.0,
        optical_classification="absorber",
    )

    evaluation = evaluate_result(result)

    assert evaluation.stability_score == 1.0
    assert evaluation.hydrogen_score == 0.0


def test_literature_count_is_preserved():
    result = ScientificResult(
        material="Material_A",
        stability_score=0.5,
        hydrogen_score=0.5,
    )

    evaluation = evaluate_result(result)

    assert evaluation.literature_count == 0


def test_evaluate_results_ranks_materials():
    results = [
        ScientificResult(
            material="Material_A",
            stability_score=0.5,
            hydrogen_score=0.4,
            band_gap=2.0,
            optical_classification="absorber",
        ),
        ScientificResult(
            material="Material_B",
            stability_score=0.9,
            hydrogen_score=0.9,
            band_gap=1.5,
            optical_classification="absorber",
        ),
    ]

    evaluations = evaluate_results(results)

    assert [item.material for item in evaluations] == [
        "Material_B",
        "Material_A",
    ]


def test_empty_results():
    assert evaluate_results([]) == []
