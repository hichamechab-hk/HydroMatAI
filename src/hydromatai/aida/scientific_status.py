from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NumericalStatus(str, Enum):
    ESTABLISHED = "NUMERICAL_STABILITY_ESTABLISHED"
    NOT_ESTABLISHED = "NUMERICAL_STABILITY_NOT_ESTABLISHED"
    INSUFFICIENT = "INSUFFICIENT_EVIDENCE"


class ScientificStatus(str, Enum):
    NOT_ESTABLISHED = "SCIENTIFIC_STATUS_NOT_ESTABLISHED"
    NUMERICAL_STABILITY_ESTABLISHED = (
        "NUMERICAL_STABILITY_ESTABLISHED"
    )
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class NumericalEvidence:
    """
    Resume de l'evidence numerique QE.

    Cette classe ne represente pas une validation scientifique.
    """

    scf_converged: int
    scf_total: int

    cutoff_status: NumericalStatus
    kpoints_status: NumericalStatus
    smearing_status: NumericalStatus

    electronic_outputs_available: bool = False

    @property
    def all_series_stable(self) -> bool:
        return (
            self.cutoff_status == NumericalStatus.ESTABLISHED
            and self.kpoints_status == NumericalStatus.ESTABLISHED
            and self.smearing_status == NumericalStatus.ESTABLISHED
        )

    @property
    def has_insufficient_series_evidence(self) -> bool:
        return any(
            status == NumericalStatus.INSUFFICIENT
            for status in (
                self.cutoff_status,
                self.kpoints_status,
                self.smearing_status,
            )
        )


@dataclass(frozen=True)
class ScientificStatusResult:
    """
    Statut scientifique prudent construit a partir
    de l'evidence numerique.

    Aucune valeur de cette classe ne signifie
    scientifiquement valide.
    """

    status: ScientificStatus
    numerical_stability: NumericalStatus
    reason: str


def evaluate_scientific_status(
    evidence: NumericalEvidence,
) -> ScientificStatusResult:
    """
    Transforme l'evidence numerique en statut scientifique prudent.

    Regles :

    1. Une convergence SCF individuelle seule ne suffit pas.
    2. Les trois series de convergence doivent etre stables.
    3. Des sorties DOS/BANDS disponibles ne constituent pas
       automatiquement une validation electronique.
    4. Si une serie manque d'evidence, le statut reste insuffisant.
    """

    if evidence.has_insufficient_series_evidence:
        return ScientificStatusResult(
            status=ScientificStatus.INSUFFICIENT_EVIDENCE,
            numerical_stability=NumericalStatus.INSUFFICIENT,
            reason=(
                "Au moins une serie de convergence ne dispose "
                "pas d'une evidence numerique suffisante."
            ),
        )

    if not evidence.all_series_stable:
        return ScientificStatusResult(
            status=ScientificStatus.NOT_ESTABLISHED,
            numerical_stability=NumericalStatus.NOT_ESTABLISHED,
            reason=(
                "Les calculs SCF peuvent etre converges individuellement, "
                "mais la stabilite numerique globale des series "
                "cutoff/k-points/smearing n'est pas etablie."
            ),
        )

    return ScientificStatusResult(
        status=ScientificStatus.NUMERICAL_STABILITY_ESTABLISHED,
        numerical_stability=NumericalStatus.ESTABLISHED,
        reason=(
            "Les trois series de convergence presentent une stabilite "
            "numerique selon les criteres fournis. Cela ne constitue "
            "pas a lui seul une validation scientifique complete."
        ),
    )
