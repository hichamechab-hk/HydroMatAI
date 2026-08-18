from dataclasses import dataclass, field
from .atom import Atom


@dataclass
class CrystalStructure:
    """
    Structure cristalline d'un matériau.
    """

    name: str
    atoms: list[Atom] = field(default_factory=list)


    def add_atom(self, atom: Atom):
        self.atoms.append(atom)


    def number_of_atoms(self):
        return len(self.atoms)
