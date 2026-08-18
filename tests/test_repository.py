from hydromatai.database import (
    create_database,
    MaterialRepository
)


def test_material_repository():

    create_database()

    repo = MaterialRepository()

    repo.add(
        {
            "name": "Water",
            "formula": "H2O"
        }
    )

    results = repo.get_by_formula("H2O")

    assert len(results) >= 1
