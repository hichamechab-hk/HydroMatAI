from hydromatai.literature import LiteratureResult
from hydromatai.scientific import analyze_material


def test_scientific_result_can_attach_literature():
    published = LiteratureResult(
        material="NU-1501-Al",
        property_name="h2_uptake",
        value=14.5,
        unit="wt%",
        year=2020,
        doi="10.1126/science.aaz8881",
    )

    result = analyze_material(
        "NU-1501-Al",
        literature_results=[published],
    )

    assert result.literature_count == 1
    assert result.literature_results[0] is published
    assert "published results=1" in result.summary
    assert result.final_score == 0.5
