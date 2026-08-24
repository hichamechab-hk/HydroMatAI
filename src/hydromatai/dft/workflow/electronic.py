from dataclasses import dataclass
from typing import Optional


from hydromatai.properties.electronic.analyzer import interpret_band_gap
@dataclass
class ElectronicWorkflowResult:
    """
    Résultat standardisé du workflow électronique.

    Workflow :

        SCF -> NSCF -> Bands -> DOS -> PDOS
    """

    candidate_id: str
    status: str = "FAILED"

    scf_success: bool = False
    nscf_success: bool = False
    bands_success: bool = False
    dos_success: bool = False
    pdos_success: bool = False

    fermi_energy: Optional[float] = None

    vbm: Optional[float] = None
    cbm: Optional[float] = None
    band_gap: Optional[float] = None

    classification: str = "unknown"

    error_type: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "PASS"


class ElectronicWorkflow:
    """
    Orchestrateur du workflow électronique HydroMatAI.

    Les calculateurs sont injectés afin de permettre :

    - tests unitaires sans QE ;
    - utilisation de Quantum ESPRESSO réel ;
    - remplacement ultérieur par un autre moteur DFT.

    Chaque calculateur doit fournir :

        prepare_input(material)
        run()

    Les étapes sont exécutées séquentiellement.
    """

    PASS = "PASS"

    FAIL_SCF = "FAIL_SCF"
    FAIL_NSCF = "FAIL_NSCF"
    FAIL_BANDS = "FAIL_BANDS"
    FAIL_DOS = "FAIL_DOS"
    FAIL_PDOS = "FAIL_PDOS"
    FAIL_ANALYSIS = "FAIL_ANALYSIS"

    def __init__(
        self,
        nscf_calculator=None,
        bands_calculator=None,
        dos_calculator=None,
        pdos_calculator=None,
    ):
        self.nscf_calculator = nscf_calculator
        self.bands_calculator = bands_calculator
        self.dos_calculator = dos_calculator
        self.pdos_calculator = pdos_calculator

    @staticmethod
    def _run_stage(calculator, material):
        """
        Prépare puis exécute une étape.
        """

        if calculator is None:
            raise RuntimeError(
                "Aucun calculateur n'a été configuré."
            )

        calculator.prepare_input(material)

        return calculator.run()

    @staticmethod
    def _successful_output(output):
        """
        Vérifie qu'une étape possède une sortie exploitable.

        Pour l'instant, la vérification reste volontairement
        légère. Les parseurs spécialisés seront intégrés ensuite.
        """

        return bool(output)

    def run(self, material, candidate_id=None):

        if candidate_id is None:
            candidate_id = (
                getattr(material, "name", None)
                or getattr(material, "formula", None)
                or "unknown"
            )

        result = ElectronicWorkflowResult(
            candidate_id=str(candidate_id)
        )

        # ======================================================
        # NSCF
        # ======================================================

        try:
            output = self._run_stage(
                self.nscf_calculator,
                material,
            )

            if not self._successful_output(output):
                raise RuntimeError(
                    "NSCF produced an empty output."
                )

            result.nscf_success = True

        except Exception as exc:
            result.status = self.FAIL_NSCF
            result.error_type = "NSCF"
            result.error_message = str(exc)
            return result

        # ======================================================
        # BANDS
        # ======================================================

        try:
            output = self._run_stage(
                self.bands_calculator,
                material,
            )

            if not self._successful_output(output):
                raise RuntimeError(
                    "Bands calculation produced an empty output."
                )

            result.bands_success = True

            # Récupération des propriétés électroniques
            # directement depuis la sortie du calcul BANDS.
            if hasattr(output, "vbm"):
                result.vbm = output.vbm

            if hasattr(output, "cbm"):
                result.cbm = output.cbm

            if hasattr(output, "band_gap"):
                result.band_gap = output.band_gap

            if result.band_gap is None:
                if result.vbm is not None and result.cbm is not None:
                    result.band_gap = result.cbm - result.vbm

        except Exception as exc:
            result.status = self.FAIL_BANDS
            result.error_type = "BANDS"
            result.error_message = str(exc)
            return result

        # ======================================================
        # DOS
        # ======================================================

        try:
            output = self._run_stage(
                self.dos_calculator,
                material,
            )

            if not self._successful_output(output):
                raise RuntimeError(
                    "DOS calculation produced an empty output."
                )

            result.dos_success = True

        except Exception as exc:
            result.status = self.FAIL_DOS
            result.error_type = "DOS"
            result.error_message = str(exc)
            return result

        # ======================================================
        # PDOS
        # ======================================================

        try:
            output = self._run_stage(
                self.pdos_calculator,
                material,
            )

            if not self._successful_output(output):
                raise RuntimeError(
                    "PDOS calculation produced an empty output."
                )

            result.pdos_success = True

        except Exception as exc:
            result.status = self.FAIL_PDOS
            result.error_type = "PDOS"
            result.error_message = str(exc)
            return result

        # ======================================================
        # ANALYSE ÉLECTRONIQUE
        # ======================================================

        interpretation = interpret_band_gap(
            result.band_gap
        )

        result.classification = interpretation.classification

        # ======================================================
        # FIN
        # ======================================================

        result.status = self.PASS

        return result
