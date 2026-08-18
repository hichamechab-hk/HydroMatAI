from abc import ABC, abstractmethod


class DFTCalculator(ABC):
    """Interface commune pour les calculateurs DFT."""

    @abstractmethod
    def prepare_input(self, material):
        """Prépare les fichiers d'entrée du calcul DFT."""
        raise NotImplementedError

    @abstractmethod
    def run(self):
        """Exécute le calcul DFT."""
        raise NotImplementedError

    @abstractmethod
    def parse_output(self):
        """Analyse les résultats du calcul DFT."""
        raise NotImplementedError
