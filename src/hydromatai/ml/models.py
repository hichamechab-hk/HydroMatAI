from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from hydromatai.ml.dataset import MaterialDataset


class MaterialModel(ABC):
    """Interface commune des futurs modèles ML HydroMatAI."""

    @abstractmethod
    def fit(self, dataset: MaterialDataset) -> None:
        """Entraîne le modèle sur un dataset supervisé."""
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: tuple[float, ...]) -> float:
        """Prédit une propriété pour un vecteur de features."""
        raise NotImplementedError


@dataclass
class PredictionResult:
    """Résultat d'une prédiction ML."""

    material_name: str
    predicted_value: float
    target_name: str
