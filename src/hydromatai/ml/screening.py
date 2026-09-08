from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hydromatai.ml.dataset import DatasetRow
from hydromatai.ml.models import MaterialModel


@dataclass(frozen=True)
class ScreeningResult:
    """Résultat d'un screening ML pour un matériau."""

    material_name: str
    predicted_value: float
    target_name: str


def screen_rows(
    model: MaterialModel,
    rows: Iterable[DatasetRow],
    target_name: str,
) -> list[ScreeningResult]:
    """
    Effectue des prédictions ML sur plusieurs matériaux.

    Cette opération ne modifie pas les données originales
    et ne lance aucun calcul DFT.
    """
    results: list[ScreeningResult] = []

    for row in rows:
        predicted_value = model.predict(row.feature_vector)

        results.append(
            ScreeningResult(
                material_name=row.material_name,
                predicted_value=float(predicted_value),
                target_name=target_name,
            )
        )

    return results


def rank_predictions(
    results: Iterable[ScreeningResult],
    reverse: bool = True,
) -> list[ScreeningResult]:
    """
    Classe les résultats du screening selon la valeur prédite.

    Par défaut, les valeurs les plus élevées apparaissent en premier.
    """
    return sorted(
        results,
        key=lambda result: result.predicted_value,
        reverse=reverse,
    )
