from __future__ import annotations

from dataclasses import dataclass

from hydromatai.core.material import Material


@dataclass(frozen=True)
class MaterialFeatures:
    """
    Descripteurs numériques de base d'un matériau.

    Cette classe ne dépend d'aucun framework ML.
    Elle constitue l'interface entre HydroMatAI et les futurs modèles.
    """

    number_of_atoms: int
    number_of_elements: int
    cell_volume: float
    cell_a: float
    cell_b: float
    cell_c: float

    @property
    def as_dict(self) -> dict[str, float | int]:
        """Retourne les features sous forme de dictionnaire."""
        return {
            "number_of_atoms": self.number_of_atoms,
            "number_of_elements": self.number_of_elements,
            "cell_volume": self.cell_volume,
            "cell_a": self.cell_a,
            "cell_b": self.cell_b,
            "cell_c": self.cell_c,
        }

    @property
    def as_vector(self) -> tuple[float, ...]:
        """Retourne les features sous forme de vecteur numérique."""
        return (
            float(self.number_of_atoms),
            float(self.number_of_elements),
            self.cell_volume,
            self.cell_a,
            self.cell_b,
            self.cell_c,
        )


def extract_features(material: Material) -> MaterialFeatures:
    """
    Extrait les features structurelles de base d'un matériau.

    Raises
    ------
    ValueError
        Si aucune structure n'est disponible.
    """
    if material.structure is None:
        raise ValueError(
            f"Impossible d'extraire les features de {material.name!r}: "
            "structure absente."
        )

    a, b, c = material.structure.cell_lengths()

    return MaterialFeatures(
        number_of_atoms=material.structure.number_of_atoms(),
        number_of_elements=material.structure.number_of_elements(),
        cell_volume=material.structure.cell_volume(),
        cell_a=a,
        cell_b=b,
        cell_c=c,
    )
