from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.ml.dataset import MaterialDataset
from hydromatai.ml.screening import (
    ScreeningResult,
    rank_predictions,
    screen_rows,
)
from hydromatai.ml.targets import ADSORPTION_ENERGY


class DummyModel:
    def predict(self, features):
        return -0.30


class VariableDummyModel:
    def __init__(self):
        self.values = [-0.10, -0.40, -0.20]
        self.index = 0

    def predict(self, features):
        value = self.values[self.index]
        self.index += 1
        return value


def make_material(name: str) -> Material:
    structure = CrystalStructure(
        name=name,
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
        name=name,
        formula="CH",
        structure=structure,
    )


def make_dataset() -> MaterialDataset:
    dataset = MaterialDataset(
        target_definition=ADSORPTION_ENERGY
    )

    dataset.add_material(
        make_material("Material_A"),
        target=-0.10,
    )

    dataset.add_material(
        make_material("Material_B"),
        target=-0.40,
    )

    dataset.add_material(
        make_material("Material_C"),
        target=-0.20,
    )

    return dataset


def test_screening_result():
    result = ScreeningResult(
        material_name="Material_A",
        predicted_value=-0.30,
        target_name="adsorption_energy",
    )

    assert result.material_name == "Material_A"
    assert result.predicted_value == -0.30
    assert result.target_name == "adsorption_energy"


def test_screen_rows():
    dataset = make_dataset()

    results = screen_rows(
        DummyModel(),
        dataset.rows,
        "adsorption_energy",
    )

    assert len(results) == 3

    assert all(
        result.target_name == "adsorption_energy"
        for result in results
    )

    assert all(
        result.predicted_value == -0.30
        for result in results
    )


def test_screen_rows_preserves_material_order():
    dataset = make_dataset()

    results = screen_rows(
        DummyModel(),
        dataset.rows,
        "adsorption_energy",
    )

    assert [result.material_name for result in results] == [
        "Material_A",
        "Material_B",
        "Material_C",
    ]


def test_rank_predictions_descending():
    results = [
        ScreeningResult("A", 0.10, "test"),
        ScreeningResult("B", 0.40, "test"),
        ScreeningResult("C", 0.20, "test"),
    ]

    ranked = rank_predictions(results)

    assert [result.material_name for result in ranked] == [
        "B",
        "C",
        "A",
    ]


def test_rank_predictions_ascending():
    results = [
        ScreeningResult("A", 0.10, "test"),
        ScreeningResult("B", 0.40, "test"),
        ScreeningResult("C", 0.20, "test"),
    ]

    ranked = rank_predictions(
        results,
        reverse=False,
    )

    assert [result.material_name for result in ranked] == [
        "A",
        "C",
        "B",
    ]


def test_screening_with_variable_predictions():
    dataset = make_dataset()

    results = screen_rows(
        VariableDummyModel(),
        dataset.rows,
        "adsorption_energy",
    )

    assert [result.predicted_value for result in results] == [
        -0.10,
        -0.40,
        -0.20,
    ]
