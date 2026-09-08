from hydromatai.literature import LiteratureRepository, LiteratureResult


def test_search_by_material_and_property():
    repository = LiteratureRepository()

    a = LiteratureResult(
        material="NU-1501-Al",
        property_name="h2_uptake",
        value=14.5,
        unit="wt%",
        doi="10.1126/science.aaz8881",
    )

    b = LiteratureResult(
        material="NU-1501-Al",
        property_name="bet_surface_area",
        value=7310,
        unit="m2/g",
        doi="10.1126/science.aaz8881",
    )

    c = LiteratureResult(
        material="MOF-5",
        property_name="h2_uptake",
        value=5.1,
        unit="wt%",
        doi="10.1002/adfm.200500561",
    )

    repository.add_many([a, b, c])

    assert len(repository.search(material="NU-1501-Al")) == 2
    assert len(repository.search(property_name="h2_uptake")) == 2
    assert len(
        repository.search(
            material="NU-1501-Al",
            property_name="h2_uptake",
        )
    ) == 1


def test_doi_normalization():
    repository = LiteratureRepository()

    result = LiteratureResult(
        material="NU-1501-Al",
        property_name="h2_uptake",
        value=14.5,
        unit="wt%",
        doi="10.1126/science.aaz8881",
    )

    repository.add(result)

    assert repository.for_doi(
        "https://doi.org/10.1126/science.aaz8881"
    ) == [result]
