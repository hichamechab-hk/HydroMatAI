from hydromatai.scientific import ScientificWorkflow


def test_workflow_produces_literature_hydrogen_score():
    workflow = ScientificWorkflow()

    result = workflow.run("NU-1501-Al")

    assert result.hydrogen_literature_score is not None
    assert result.hydrogen_literature_score.available_criteria > 0
    assert 0.0 <= result.hydrogen_literature_score.final_score <= 1.0


def test_mgh2_has_literature_hydrogen_score():
    workflow = ScientificWorkflow()

    result = workflow.run("MgH2")

    assert result.hydrogen_literature_score is not None
    assert result.hydrogen_literature_score.gravimetric_score > 0
