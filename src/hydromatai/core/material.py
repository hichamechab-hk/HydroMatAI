from __future__ import annotations

from dataclasses import dataclass

from .structure import CrystalStructure


@dataclass
class Material:
    """
    Modèle principal d'un matériau HydroMatAI.
    """

    name: str
    formula: str
    structure: CrystalStructure | None = None

    def info(self) -> dict[str, str]:
        """Informations d'identification du matériau."""
        return {
            "name": self.name,
            "formula": self.formula,
        }

    def number_of_atoms(self) -> int:
        """Nombre d'atomes si une structure est disponible."""
        if self.structure is None:
            return 0

        return self.structure.number_of_atoms()

    def structure_volume(self) -> float | None:
        """Volume de cellule en Angstrom^3."""
        if self.structure is None:
            return None

        return self.structure.cell_volume()

    def elements(self) -> list[str]:
        """Éléments présents dans la structure."""
        if self.structure is None:
            return []

        return self.structure.elements()
