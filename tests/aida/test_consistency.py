from hydromatai.aida.consistency import analyze_consistency
from hydromatai.aida.semantic import build_semantic_evidence


def test_consistency_tifeh2():
    evidence = build_semantic_evidence("TiFeH2")
    findings = analyze_consistency("TiFeH2", evidence)

    assert findings


def test_final_score_warning():
    evidence = build_semantic_evidence("TiFeH2")
    findings = analyze_consistency("TiFeH2", evidence)

    warnings = [
        item for item in findings
        if item.category == "WARNING"
        and "final_screening_score" in item.message
    ]

    assert warnings


def test_qe_campaign_separation():
    evidence = build_semantic_evidence("TiFeH2")
    findings = analyze_consistency("TiFeH2", evidence)

    separation = [
        item for item in findings
        if "deux générations de données QE" in item.message
    ]

    assert separation


def test_literature_fact():
    evidence = build_semantic_evidence("TiFeH2")
    findings = analyze_consistency("TiFeH2", evidence)

    facts = [
        item for item in findings
        if item.category == "FACT"
        and "LITERATURE" in item.message
    ]

    assert facts
