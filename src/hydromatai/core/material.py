from dataclasses import dataclass
from .structure import CrystalStructure


@dataclass
class Material:

    name: str
    formula: str
    structure: CrystalStructure | None = None


    def info(self):
        return {
            "name": self.name,
            "formula": self.formula
        }
