from hydromatai.scientific import ScientificWorkflow


def test_multiple_materials_are_supported():
    workflow = ScientificWorkflow()

    nu1501 = workflow.run("NU-1501-Al")
    mof5 = workflow.run("MOF-5")

    assert nu1501.literature_count == 6
    assert mof5.literature_count == 4

    nu_properties = {
        item.property_name
        for item in nu1501.literature_results
    }

    mof5_properties = {
        item.property_name
        for item in mof5.literature_results
    }

    assert "h2_uptake" in nu_properties
    assert "bet_surface_area" in nu_properties

    assert "h2_uptake" in mof5_properties
    assert "heat_of_adsorption" in mof5_properties


def test_unknown_material_is_isolated():
    workflow = ScientificWorkflow()

    result = workflow.run("UNKNOWN-MATERIAL")

    assert result.literature_count == 0
