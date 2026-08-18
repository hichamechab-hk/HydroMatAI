from hydromatai.database import (
    create_database,
    MaterialRecord,
    MaterialRepository,
)


def test_material_repository():

    create_database()

    repo = MaterialRepository()

    material = MaterialRecord(
        name="Water",
        formula="H2O",
    )

    repo.add(material)

    result = repo.get_by_formula("H2O")

    assert result is material
    assert result.formula == "H2O"
