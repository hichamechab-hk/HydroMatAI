from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from math import sqrt

from .atom import Atom


@dataclass
class CrystalStructure:
    """
    Structure cristalline d'un matériau.

    Les vecteurs de cellule sont exprimés en Angstrom.
    """

    name: str
    atoms: list[Atom] = field(default_factory=list)

    cell: list[list[float]] = field(
        default_factory=lambda: [
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
        ]
    )

    def __post_init__(self) -> None:
        if len(self.cell) != 3 or any(len(row) != 3 for row in self.cell):
            raise ValueError("La cellule doit être une matrice 3x3.")

    def add_atom(self, atom: Atom) -> None:
        """Ajoute un atome à la structure."""
        if not isinstance(atom, Atom):
            raise TypeError("atom doit être une instance de Atom.")

        self.atoms.append(atom)

    def number_of_atoms(self) -> int:
        """Nombre total d'atomes."""
        return len(self.atoms)

    def composition(self) -> dict[str, int]:
        """
        Retourne la composition élémentaire.

        Exemple
        -------
        {"C": 6, "H": 4, "Zn": 1}
        """
        return dict(Counter(atom.element for atom in self.atoms))

    def elements(self) -> list[str]:
        """Retourne les éléments présents, triés."""
        return sorted(self.composition())

    def number_of_elements(self) -> int:
        """Nombre d'éléments chimiques distincts."""
        return len(self.composition())

    def atomic_fractions(self) -> dict[str, float]:
        """Retourne les fractions atomiques."""
        total = self.number_of_atoms()

        if total == 0:
            return {}

        return {
            element: count / total
            for element, count in self.composition().items()
        }

    def cell_volume(self) -> float:
        """
        Calcule le volume de la cellule en Angstrom^3.

        Utilise le déterminant de la matrice 3x3.
        """
        a, b, c = self.cell

        volume = (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )

        return abs(float(volume))

    def cell_lengths(self) -> tuple[float, float, float]:
        """Longueurs des trois vecteurs de cellule en Angstrom."""

        def norm(vector: list[float]) -> float:
            return sqrt(sum(float(x) ** 2 for x in vector))

        return tuple(norm(vector) for vector in self.cell)

    def formula(self) -> str:
        """
        Construit une formule simple à partir de la composition.

        Les éléments sont triés alphabétiquement.
        """
        parts = []

        for element, count in sorted(self.composition().items()):
            parts.append(element)
            if count != 1:
                parts.append(str(count))

        return "".join(parts)
