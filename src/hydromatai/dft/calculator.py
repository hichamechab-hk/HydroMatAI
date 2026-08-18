from abc import ABC, abstractmethod
from typing import Any


class DFTCalculator(ABC):
    """
    Interface commune pour les moteurs DFT de HydroMatAI.
    """

    @abstractmethod
    def prepare_input(self, material: Any) -> str:
        """
        Prépare les fichiers d'entrée DFT.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self, material: Any) -> Any:
        """
        Lance le calcul DFT.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_output(self, output: str) -> Any:
        """
        Analyse les résultats du calcul DFT.
        """
        raise NotImplementedError
