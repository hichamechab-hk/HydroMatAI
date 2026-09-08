from hydromatai.literature import (
    LiteratureResult,
    calculate_hydrogen_storage_score,
)


def test_high_confidence():
    results = [
        LiteratureResult(
            material="Material-A",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Material-A",
            property_name="h2_uptake",
            value=50.0,
            unit="g/L",
        ),
        LiteratureResult(
            material="Material-A",
            property_name="h2_deliverable_capacity",
            value=7.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Material-A",
            property_name="bet_surface_area",
            value=4000.0,
            unit="m2/g",
        ),
        LiteratureResult(
            material="Material-A",
            property_name="desorption_temperature",
            value=200.0,
            unit="degC",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Material-A",
        results,
    )

    assert score.available_criteria == 5
    assert score.confidence == "HIGH"


def test_medium_confidence():
    results = [
        LiteratureResult(
            material="Material-B",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Material-B",
            property_name="bet_surface_area",
            value=4000.0,
            unit="m2/g",
        ),
        LiteratureResult(
            material="Material-B",
            property_name="desorption_temperature",
            value=200.0,
            unit="degC",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Material-B",
        results,
    )

    assert score.available_criteria == 3
    assert score.confidence == "MEDIUM"


def test_low_confidence():
    results = [
        LiteratureResult(
            material="Material-C",
            property_name="h2_uptake",
            value=5.0,
            unit="wt%",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Material-C",
        results,
    )

    assert score.available_criteria == 1
    assert score.confidence == "LOW"
