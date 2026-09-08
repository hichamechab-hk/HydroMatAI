import pytest

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
    assert row.material_name == "TestMaterial"
    assert row.formula == "CH"
    assert row.target == -0.25


def test_feature_matrix():
    dataset = MaterialDataset()

    dataset.add_material(make_material(), target=-0.25)

    assert len(dataset.feature_matrix) == 1
    assert dataset.feature_matrix[0] == (
        2.0,
        2.0,
        1000.0,
        10.0,
        10.0,
        10.0,
    )


def test_targets():
    dataset = MaterialDataset()

    dataset.add_material(make_material(), target=-0.25)

    assert dataset.targets == [-0.25]


def test_supervised_rows():
    dataset = MaterialDataset()

    dataset.add_material(make_material(), target=-0.25)

    assert len(dataset.supervised_rows()) == 1
    assert dataset.supervised_rows()[0].target == -0.25


def test_feature_vector_matches_features():
    dataset = MaterialDataset()

    row = dataset.add_material(make_material(), target=-0.25)

    assert row.feature_vector == row.features.as_vector


def test_dataset_target_definition():
    from hydromatai.ml.targets import ADSORPTION_ENERGY

    dataset = MaterialDataset(
        target_definition=ADSORPTION_ENERGY
    )

    material = make_material()

    row = dataset.add_material(
        material,
        target=-0.25,
    )

    assert row.target == -0.25
    assert row.target_definition == ADSORPTION_ENERGY
    assert dataset.target_definition == ADSORPTION_ENERGY
