from hydromatai.literature import LiteratureRepository, LiteratureResult


def make_result(
    material: str = "NU-1501-Al",
    property_name: str = "h2_uptake",
    value: float = 14.5,
    unit: str = "wt%",
) -> LiteratureResult:
    return LiteratureResult(
        material=material,
        property_name=property_name,
        value=value,
        unit=unit,
        year=2020,
        doi="10.1126/science.aaz8881",
    )


def test_repository_rejects_duplicate_result():
    repository = LiteratureRepository()

    first = make_result()
    second = make_result()

    assert repository.add(first) is True
    assert repository.add(second) is False
    assert len(repository) == 1


def test_repository_allows_different_properties_from_same_article():
    repository = LiteratureRepository()

    uptake = make_result(
        property_name="h2_uptake",
        value=14.5,
        unit="wt%",
    )

    surface = make_result(
        property_name="bet_surface_area",
        value=7310.0,
        unit="m2/g",
    )

    assert repository.add(uptake) is True
    assert repository.add(surface) is True
    assert len(repository) == 2


def test_repository_search_by_doi():
    repository = LiteratureRepository()

    result = make_result()
    repository.add(result)

    matches = repository.for_doi("10.1126/SCIENCE.AAZ8881")

    assert matches == [result]
