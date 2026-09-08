from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.ml.dataset import MaterialDataset
from hydromatai.ml.models import MaterialModel, PredictionResult
from hydromatai.ml.prediction import PredictionRequest, predict_row


class DummyModel(MaterialModel):
    """Modèle minimal pour tester l'interface ML."""

    def fit(self, dataset: MaterialDataset) -> None:
        self.fitted = True

    def predict(self, features: tuple[float, ...]) -> float:
        return sum(features)


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


def test_dummy_model_implements_interface():
    model = DummyModel()

    dataset = MaterialDataset()
    dataset.add_material(make_material(), target=-0.25)

    model.fit(dataset)

    assert model.fitted is True


def test_dummy_model_prediction():
    model = DummyModel()

    prediction = model.predict((1.0, 2.0, 3.0))

    assert prediction == 6.0


def test_prediction_request():
    dataset = MaterialDataset()
    row = dataset.add_material(make_material(), target=-0.25)

    request = PredictionRequest(
        row=row,
        target_name="adsorption_energy",
    )

    assert request.row is row
    assert request.target_name == "adsorption_energy"


def test_predict_row():
    model = DummyModel()

    dataset = MaterialDataset()
    row = dataset.add_material(make_material(), target=-0.25)

    request = PredictionRequest(
        row=row,
        target_name="adsorption_energy",
    )

    result = predict_row(model, request)

    assert isinstance(result, PredictionResult)
    assert result.material_name == "TestMaterial"
    assert result.target_name == "adsorption_energy"
    assert result.predicted_value == sum(row.feature_vector)
