"""Machine-learning utilities for HydroMatAI."""

from .dataset import DatasetRow, MaterialDataset
from .features import MaterialFeatures, extract_features
from .models import MaterialModel, PredictionResult
from .prediction import PredictionRequest, predict_row
from .screening import ScreeningResult, rank_predictions, screen_rows
from .targets import (
    ADSORPTION_ENERGY,
    AVAILABLE_TARGETS,
    BAND_GAP,
    TOTAL_ENERGY,
    TargetDefinition,
)

__all__ = [
    "DatasetRow",
    "MaterialDataset",
    "MaterialFeatures",
    "extract_features",
    "MaterialModel",
    "PredictionResult",
    "PredictionRequest",
    "predict_row",
    "ScreeningResult",
    "screen_rows",
    "rank_predictions",
    "TargetDefinition",
    "ADSORPTION_ENERGY",
    "BAND_GAP",
    "TOTAL_ENERGY",
    "AVAILABLE_TARGETS",
]
