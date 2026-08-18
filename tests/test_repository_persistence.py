from hydromatai.database import MaterialRecord, MaterialRepository


def test_repository_persistence():

    repository = MaterialRepository()

    material = MaterialRecord(
        formula="Fe2O3",
        name="Iron oxide",
    )

    repository.add(material)

    new_repository = MaterialRepository()

    result = new_repository.get_by_formula("Fe2O3")

    assert result is not None
    assert result.formula == "Fe2O3"
    assert result.name == "Iron oxide"
