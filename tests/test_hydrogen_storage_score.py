from hydromatai.literature import (
    LiteratureResult,
    calculate_hydrogen_storage_score,
)


def test_hydrogen_storage_score():
    results = [
        LiteratureResult(
            material="Test-MOF",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test-MOF",
            property_name="h2_uptake",
            value=50.0,
            unit="g/L",
        ),
        LiteratureResult(
            material="Test-MOF",
            property_name="bet_surface_area",
            value=4000.0,
            unit="m2/g",
        ),
        LiteratureResult(
            material="Test-MOF",
            property_name="desorption_temperature",
            value=200.0,
            unit="degC",
        ),
    ]

    score = calculate_hydrogen_storage_score(
        "Test-MOF",
        results,
    )

    assert score.material == "Test-MOF"
    assert score.available_criteria == 4
    assert score.gravimetric_score == 0.8
    assert score.volumetric_score == round(50.0 / 70.0, 4)
    assert score.surface_area_score == 0.8
    assert score.thermal_score == round((400 - 200) / 300, 4)
    assert 0.0 <= score.final_score <= 1.0


def test_hydrogen_storage_score_unknown_material():
    results = [
        LiteratureResult(
            material="MOF-5",
            property_name="h2_uptake",
            value=5.1,
            unit="wt%",
        )
    ]

    score = calculate_hydrogen_storage_score(
        "UNKNOWN",
        results,
    )

    assert score.available_criteria == 0
    assert score.final_score == 0.0


def test_theoretical_capacity_is_supported():
    results = [
        LiteratureResult(
            material="MgH2",
            property_name="h2_theoretical_capacity",
            value=7.6,
            unit="wt%",
        )
    ]

    score = calculate_hydrogen_storage_score(
        "MgH2",
        results,
    )

    assert score.available_criteria == 1
    assert score.gravimetric_score == 0.76
