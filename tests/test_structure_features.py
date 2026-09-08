from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.ml.features import extract_features


def test_structure_composition():
    structure = CrystalStructure("test")

    structure.add_atom(Atom("C", 0.0, 0.0, 0.0))
    structure.add_atom(Atom("C", 0.5, 0.5, 0.5))
    structure.add_atom(Atom("H", 0.2, 0.2, 0.2))

    assert structure.number_of_atoms() == 3
    assert structure.composition() == {"C": 2, "H": 1}
    assert structure.number_of_elements() == 2


def test_structure_volume():
    structure = CrystalStructure(
        "cube",
        cell=[
            [10.0, 0.0, 0.0],
            [0.0, 20.0, 0.0],
            [0.0, 0.0, 30.0],
        ],
    )

    assert structure.cell_volume() == 6000.0


def test_structure_cell_lengths():
    structure = CrystalStructure(
        "cell",
        cell=[
            [3.0, 0.0, 0.0],
            [0.0, 4.0, 0.0],
            [0.0, 0.0, 5.0],
        ],
    )

    assert structure.cell_lengths() == (3.0, 4.0, 5.0)


def test_material_features():
    structure = CrystalStructure(
        "test",
        atoms=[
            Atom("C", 0.0, 0.0, 0.0),
            Atom("H", 0.5, 0.5, 0.5),
        ],
        cell=[
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
        ],
    )

    material = Material(
        name="TestMaterial",
        formula="CH",
        structure=structure,
    )

    features = extract_features(material)

    assert features.number_of_atoms == 2
    assert features.number_of_elements == 2
    assert features.cell_volume == 1000.0
    assert features.cell_a == 10.0
    assert features.cell_b == 10.0
    assert features.cell_c == 10.0


def test_features_vector():
    structure = CrystalStructure(
        "test",
        cell=[
            [2.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 0.0, 4.0],
        ],
    )

    material = Material(
        name="Test",
        formula="X",
        structure=structure,
    )

    features = extract_features(material)

    assert features.as_vector == (
        0.0,
        0.0,
        24.0,
        2.0,
        3.0,
        4.0,
    )


def test_features_require_structure():
    material = Material(
        name="NoStructure",
        formula="H2",
    )

    try:
        extract_features(material)
    except ValueError as exc:
        assert "structure absente" in str(exc)
    else:
        raise AssertionError("ValueError attendu")
