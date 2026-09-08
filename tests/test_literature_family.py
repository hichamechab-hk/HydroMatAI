from hydromatai.literature import (
    LiteratureRepository,
    LiteratureResult,
    infer_material_family,
)


def test_family_inference():
    assert infer_material_family("MOF-5") == "MOF"
    assert infer_material_family("NU-1501-Al") == "MOF"
    assert infer_material_family("MgH2") == "HYDRIDE"
    assert infer_material_family("NaAlH4") == "HYDRIDE"
    assert infer_material_family("MgH2-LiAlH4") == "HYBRID"


def test_family_is_stored():
    result = LiteratureResult(
        material="MgH2",
        property_name="h2_storage_capacity",
        value=7.6,
        unit="wt%",
    )

    assert result.family == "HYDRIDE"


def test_repository_filters_by_family():
    repository = LiteratureRepository()

    repository.add(
        LiteratureResult(
            material="MOF-5",
            property_name="h2_uptake",
            value=5.1,
            unit="wt%",
        )
    )

    repository.add(
        LiteratureResult(
            material="MgH2",
            property_name="h2_storage_capacity",
            value=7.6,
            unit="wt%",
        )
    )

    repository.add(
        LiteratureResult(
            material="MgH2-LiAlH4",
            property_name="h2_storage_capacity",
            value=9.5,
            unit="wt%",
        )
    )

    assert len(repository.for_family("MOF")) == 1
    assert len(repository.for_family("HYDRIDE")) == 1
    assert len(repository.for_family("HYBRID")) == 1
