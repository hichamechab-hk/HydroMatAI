from hydromatai.scientific import ScientificWorkflow


def test_workflow_loads_published_results():
    workflow = ScientificWorkflow()

    assert len(workflow.literature_repository) >= 40


def test_workflow_attaches_published_results_to_material():
    workflow = ScientificWorkflow()

    result = workflow.run("NU-1501-Al")

    assert result.material == "NU-1501-Al"
    assert result.literature_count == 6

    properties = {
        item.property_name
        for item in result.literature_results
    }

    assert "bet_surface_area" in properties
    assert "h2_uptake" in properties
    assert "h2_deliverable_capacity" in properties


def test_workflow_unknown_material_has_no_literature():
    workflow = ScientificWorkflow()

    result = workflow.run("UNKNOWN-MATERIAL")

    assert result.literature_count == 0


def test_workflow_keeps_existing_scientific_score():
    workflow = ScientificWorkflow()

    result = workflow.run("NU-1501-Al")

    assert result.final_score == 0.5
