from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.ml.dataset import DatasetRow, MaterialDataset


def make_material() -> Material:
    structure = CrystalStructure(
        name="TestMaterial",
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

    return Material(
        name="TestMaterial",
        formula="CH",
        structure=structure,
    )


def test_add_material():
    dataset = MaterialDataset()
    material = make_material()

    row = dataset.add_material(material, target=-0.25)

    assert isinstance(row, DatasetRow)
    assert len(dataset) == 1
    assert row.material_name == "TestMaterial"
    assert row.formula == "CH"
    assert row.target == -0.25


def test_feature_matrix():
    dataset = MaterialDataset()
    dataset.add_material(make_material(), target=-0.25)

    matrix = dataset.feature_matrix

    assert len(matrix) == 1
    assert len(matrix[0]) == 6
    assert matrix[0][0] == 2.0
    assert matrix[0][1] == 2.0
    assert matrix[0][2] == 1000.0


def test_targets():
    dataset = MaterialDataset()

    dataset.add_material(make_material(), target=-0.25)
    dataset.add_material(make_material())

    assert dataset.targets == [-0.25, None]


def test_supervised_rows():
    dataset = MaterialDataset()

    dataset.add_material(make_material(), target=-0.25)
    dataset.add_material(make_material())

    rows = dataset.supervised_rows()

    assert len(rows) == 1
    assert rows[0].target == -0.25


def test_empty_dataset():
    dataset = MaterialDataset()

    assert len(dataset) == 0
    assert dataset.feature_matrix == []
    assert dataset.targets == []
    assert dataset.supervised_rows() == []


def test_feature_vector_matches_features():
    dataset = MaterialDataset()
    row = dataset.add_material(make_material(), target=-0.25)

    assert row.feature_vector == row.features.as_vector
