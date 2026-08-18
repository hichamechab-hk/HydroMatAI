from dataclasses import dataclass


@dataclass
class Atom:
    """
    Représente un atome dans un matériau.
    """

    symbol: str
    x: float
    y: float
    z: float

    def position(self):
        return (self.x, self.y, self.z)
