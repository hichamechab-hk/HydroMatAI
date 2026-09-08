from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Atom:
    """
    Représente un atome dans une structure cristalline.

    Parameters
    ----------
    symbol:
        Symbole chimique de l'élément.
    x, y, z:
        Coordonnées de l'atome.
    """

    symbol: str
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        self.symbol = self.symbol.strip()

        if not self.symbol:
            raise ValueError("Le symbole chimique ne peut pas être vide.")

    @property
    def element(self) -> str:
        """Alias compatible avec l'ancienne API."""
        return self.symbol

    @property
    def coordinates(self) -> tuple[float, float, float]:
        """Retourne les coordonnées sous forme de tuple."""
        return (float(self.x), float(self.y), float(self.z))
