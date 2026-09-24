from .models import AIDAResult, Evidence, Finding
from .scientific_status import (
    NumericalEvidence,
    evaluate_scientific_status,
)


class AIDAAnalyzer:
    """Initial rule-based scientific analyzer for HydroMatAI."""

    def analyze(
        self,
        subject: str,
        evidence: list[Evidence] | None = None,
        numerical_evidence: NumericalEvidence | None = None,
    ) -> AIDAResult:
        evidence = evidence or []

        result = AIDAResult(subject=subject)

        for item in evidence:
            category = item.metadata.get(
                "category",
                item.status,
            )

            result.findings.append(
                Finding(
                    category=str(category),
                    message=(
                        f"{item.name}: valeur={item.value!r}; "
                        f"source={item.source}; statut={item.status}"
                    ),
                    severity="INFO",
                    evidence=[item],
                )
            )

        if not evidence:
            result.warnings.append(
                "Aucune preuve ou donnée source fournie à AIDA."
            )

        if numerical_evidence is not None:
            scientific_result = evaluate_scientific_status(
                numerical_evidence
            )

            result.metadata["scientific_status"] = (
                scientific_result.status.value
            )
            result.metadata["numerical_stability"] = (
                scientific_result.numerical_stability.value
            )
            result.metadata["scientific_status_reason"] = (
                scientific_result.reason
            )

        return result
