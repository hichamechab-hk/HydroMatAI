from __future__ import annotations

from dataclasses import dataclass

from hydromatai.ml.dataset import DatasetRow
from hydromatai.ml.models import MaterialModel, PredictionResult


@dataclass(frozen=True)
class PredictionRequest:
    """Demande de prédiction pour un matériau."""

    row: DatasetRow
    target_name: str


def predict_row(
    model: MaterialModel,
    request: PredictionRequest,
) -> PredictionResult:
    """Effectue une prédiction pour une observation du dataset."""
    predicted_value = model.predict(request.row.feature_vector)

    return PredictionResult(
        material_name=request.row.material_name,
        predicted_value=predicted_value,
        target_name=request.target_name,
    )
