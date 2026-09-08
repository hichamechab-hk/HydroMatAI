from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetDefinition:
    """
    Définition d'une propriété scientifique utilisée comme cible ML.
    """

    name: str
    unit: str
    description: str

    def validate_value(self, value: float | None) -> bool:
        """Vérifie qu'une valeur de target est exploitable."""
        return value is not None


ADSORPTION_ENERGY = TargetDefinition(
    name="adsorption_energy",
    unit="eV",
    description=(
        "Énergie d'adsorption de H2 calculée à partir des énergies "
        "du complexe, de l'hôte et de H2."
    ),
)


BAND_GAP = TargetDefinition(
    name="band_gap",
    unit="eV",
    description="Énergie de gap électronique du matériau.",
)


TOTAL_ENERGY = TargetDefinition(
    name="total_energy",
    unit="eV",
    description="Énergie totale calculée du matériau.",
)


AVAILABLE_TARGETS: tuple[TargetDefinition, ...] = (
    ADSORPTION_ENERGY,
    BAND_GAP,
    TOTAL_ENERGY,
)
