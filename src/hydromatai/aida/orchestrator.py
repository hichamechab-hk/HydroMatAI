from .analyzer import AIDAAnalyzer
from .models import AIDAResult, Evidence
from .scientific_status import NumericalEvidence


class AIDA:
    """Main AIDA interface for HydroMatAI."""

    def __init__(self) -> None:
        self.analyzer = AIDAAnalyzer()

    def analyze(
        self,
        subject: str,
        evidence: list[Evidence] | None = None,
        numerical_evidence: NumericalEvidence | None = None,
    ) -> AIDAResult:
        return self.analyzer.analyze(
            subject,
            evidence,
            numerical_evidence,
        )
