from hydromatai.literature import (
    LiteratureResult,
    calculate_objective_score,
    rank_by_objective,
)


def test_global_objective():
    results = [
        LiteratureResult(
            material="Test",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test",
            property_name="h2_uptake",
            value=50.0,
            unit="g/L",
        ),
        LiteratureResult(
            material="Test",
            property_name="bet_surface_area",
            value=4000.0,
            unit="m2/g",
        ),
        LiteratureResult(
            material="Test",
            property_name="desorption_temperature",
            value=200.0,
            unit="degC",
        ),
    ]

    score = calculate_objective_score(
        "Test",
        results,
        "GLOBAL",
    )

    assert score.objective == "GLOBAL"
    assert 0.0 <= score.screening_score <= 1.0
    assert score.coverage == 1.0
    assert score.confidence == "HIGH"


def test_invalid_objective():
    try:
        calculate_objective_score(
            "Test",
            [],
            "INVALID",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError expected")


def test_rank_by_objective():
    results = [
        LiteratureResult(
            material="A",
            property_name="h2_uptake",
            value=5.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="B",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
    ]

    ranking = rank_by_objective(
        results,
        "HIGH_DENSITY",
    )

    assert ranking[0].material == "B"
