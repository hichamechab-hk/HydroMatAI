from hydromatai.literature import (
    rank_by_property,
    summarize_by_family,
    LiteratureResult,
    compare_material,
    rank_by_published_h2_uptake,
)


def test_compare_material():
    results = [
        LiteratureResult(
            material="Test-MOF",
            property_name="h2_uptake",
            value=8.5,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test-MOF",
            property_name="h2_deliverable_capacity",
            value=7.2,
            unit="wt%",
        ),
        LiteratureResult(
            material="Test-MOF",
            property_name="bet_surface_area",
            value=4500,
            unit="m2/g",
        ),
    ]

    comparison = compare_material("Test-MOF", results)

    assert comparison.result_count == 3
    assert comparison.best_h2_uptake_wt_percent == 8.5
    assert comparison.best_deliverable_wt_percent == 7.2
    assert comparison.best_surface_area_m2_g == 4500


def test_compare_unknown_material():
    results = [
        LiteratureResult(
            material="MOF-5",
            property_name="h2_uptake",
            value=5.1,
            unit="wt%",
        ),
    ]

    comparison = compare_material("UNKNOWN", results)

    assert comparison.result_count == 0
    assert comparison.best_h2_uptake_wt_percent is None


def test_rank_by_published_h2_uptake():
    results = [
        LiteratureResult(
            material="MOF-A",
            property_name="h2_uptake",
            value=5.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="MOF-B",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="MOF-C",
            property_name="h2_uptake",
            value=6.0,
            unit="wt%",
        ),
    ]

    ranking = rank_by_published_h2_uptake(results)

    assert [item.material for item in ranking] == [
        "MOF-B",
        "MOF-C",
        "MOF-A",
    ]


def test_rank_by_property_and_unit():
    results = [
        LiteratureResult(
            material="MOF-A",
            property_name="h2_uptake",
            value=5.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="MOF-B",
            property_name="h2_uptake",
            value=8.0,
            unit="wt%",
        ),
        LiteratureResult(
            material="MOF-C",
            property_name="h2_uptake",
            value=100.0,
            unit="g/L",
        ),
    ]

    ranking = rank_by_property(
        results,
        "h2_uptake",
        "wt%",
    )

    assert [item.material for item in ranking] == [
        "MOF-B",
        "MOF-A",
    ]


def test_summarize_by_family():
    results = [
        LiteratureResult(
            material="MOF-5",
            property_name="h2_uptake",
            value=5.1,
            unit="wt%",
        ),
        LiteratureResult(
            material="MgH2",
            property_name="h2_storage_capacity",
            value=7.6,
            unit="wt%",
        ),
    ]

    summary = summarize_by_family(results)

    assert "MOF" in summary
    assert "HYDRIDE" in summary
    assert summary["MOF"][0].material == "MOF-5"
    assert summary["HYDRIDE"][0].material == "MgH2"
