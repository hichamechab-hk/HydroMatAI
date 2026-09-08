from hydromatai.literature import (
    LiteratureResult,
    calculate_hydrogen_storage_score,
)


def test_screening_score_uses_data_coverage():
    results = [
        LiteratureResult(
            material="Test-A",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Test-A",
        results,
    )

    assert score.available_criteria == 1
    assert score.coverage == 0.2
    assert score.screening_score == round(
        score.final_score * 0.2,
        4,
    )


def test_full_coverage_keeps_raw_score():
    results = [
        LiteratureResult(
            material="Test-B",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test-B",
            property_name="h2_uptake",
            value=50.0,
            unit="g/L",
        ),
        LiteratureResult(
            material="Test-B",
            property_name="h2_deliverable_capacity",
            value=7.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test-B",
            property_name="bet_surface_area",
            value=4000.0,
            unit="m2/g",
        ),
        LiteratureResult(
            material="Test-B",
            property_name="desorption_temperature",
            value=200.0,
            unit="degC",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Test-B",
        results,
    )

    assert score.coverage == 1.0
    assert score.screening_score == score.final_score
