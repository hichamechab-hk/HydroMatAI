class DFTError(Exception):
    """
    Erreur générale du moteur DFT.
    """


class DFTInputError(DFTError):
    """
    Erreur lors de la préparation des entrées DFT.
    """


class DFTRunError(DFTError):
    """
    Erreur pendant l'exécution du calcul DFT.
    """


class DFTParseError(DFTError):
    """
    Erreur lors de l'analyse des résultats DFT.
    """
