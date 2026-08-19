import re

from hydromatai.dft.output import DFTResult
from hydromatai.dft.exceptions import DFTParseError


class QEParser:
    """
    Analyse la sortie texte de Quantum ESPRESSO pw.x.
    """

    ENERGY_PATTERN = re.compile(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry"
    )

    def parse(self, raw_output: str) -> DFTResult:
        """
        Extrait les résultats principaux de Quantum ESPRESSO.
        """

        if not raw_output:
            raise DFTParseError(
                "La sortie Quantum ESPRESSO est vide."
            )

        # --------------------------------------------------------
        # Recherche de l'énergie totale
        # --------------------------------------------------------

        matches = self.ENERGY_PATTERN.findall(raw_output)

        if not matches:
            raise DFTParseError(
                "Impossible de trouver l'énergie totale dans la sortie QE."
            )

        # La dernière énergie correspond à l'énergie finale SCF
        total_energy = float(matches[-1])

        # Si une énergie valide est trouvée,
        # le parsing est considéré comme réussi.
        success = True

        return DFTResult(
            success=success,
            total_energy=total_energy,
            band_gap=None,
            forces=None,
            raw_output=raw_output,
        )
