from hydromatai.database import MaterialRecord, MaterialRepository


def test_material_repository_records():

    repository = MaterialRepository()

    material = MaterialRecord(
        formula="TiO2",
        name="Titanium dioxide",
    )

    repository.add(material)

    result = repository.get_by_formula("TiO2")

    assert result is material
    assert result.formula == "TiO2"


def test_material_repository_list_all():

    repository = MaterialRepository()

    repository.add(MaterialRecord(formula="TiO2"))
    repository.add(MaterialRecord(formula="H2O"))

    materials = repository.list_all()

    assert len(materials) == 2
    assert materials[0].formula == "TiO2"
    assert materials[1].formula == "H2O"
