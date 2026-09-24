from hydromatai.aida.semantic import build_semantic_evidence


def test_semantic_evidence_tifeh2():
    evidence = build_semantic_evidence("TiFeH2")

    assert evidence

    names = {item.name for item in evidence}

    assert "h2_uptake_wt_percent" in names
    assert "ambient_score" in names
    assert "scientific_score" in names
    assert "scientific_corrected" in names
    assert "final_screening_score" in names


def test_final_score_is_not_dft_validation():
    evidence = build_semantic_evidence("TiFeH2")

    item = next(
        item for item in evidence
        if item.name == "final_screening_score"
    )

    assert item.value == 0.991579
    assert item.status == "COMPOSITE"
    assert item.metadata["category"] == "COMPOSITE_SCREENING"
    assert item.metadata["independent_dft_validation"] is False


def test_h2_is_literature():
    evidence = build_semantic_evidence("TiFeH2")

    item = next(
        item for item in evidence
        if item.name == "h2_uptake_wt_percent"
    )

    assert item.value == 1.86
    assert item.metadata["category"] == "LITERATURE"
    assert item.metadata["unit"] == "wt%"
