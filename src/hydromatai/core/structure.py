from dataclasses import dataclass, field
from .atom import Atom


@dataclass
class CrystalStructure:
    """
    Structure cristalline d'un matériau.
    """

    name: str
    atoms: list[Atom] = field(default_factory=list)

    # Vecteurs de cellule en Angstrom
    cell: list[list[float]] = field(
        default_factory=lambda: [
            [10.0, 0.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
        ]
    )

    def add_atom(self, atom: Atom):
        self.atoms.append(atom)

    def number_of_atoms(self):
        return len(self.atoms)
