from __future__ import annotations

from .models import Evidence, Finding


def analyze_consistency(subject: str, evidence: list[Evidence]) -> list[Finding]:
    """
    Analyze provenance consistency without recalculating scientific values.

    READ-ONLY:
    - no QE execution
    - no score recalculation
    - no modification of scientific data
    """
    findings: list[Finding] = []

    categories = {
        item.metadata.get("category")
        for item in evidence
    }

    # ------------------------------------------------------------------
    # Literature H2
    # ------------------------------------------------------------------
    literature_h2 = [
        item for item in evidence
        if item.name == "h2_uptake_wt_percent"
        and item.metadata.get("category") == "LITERATURE"
    ]

    for item in literature_h2:
        findings.append(
            Finding(
                category="FACT",
                message=(
                    f"{subject}: H2 uptake = {item.value} {item.metadata.get('unit', '')} "
                    f"provient d'une source LITERATURE."
                ).strip(),
                severity="INFO",
                evidence=[item],
            )
        )

    # ------------------------------------------------------------------
    # Final composite score
    # ------------------------------------------------------------------
    composite = [
        item for item in evidence
        if item.name == "final_screening_score"
    ]

    for item in composite:
        findings.append(
            Finding(
                category="WARNING",
                message=(
                    f"{subject}: final_screening_score = {item.value} "
                    "est un score composite HYDROMATAI et ne constitue "
                    "pas une validation DFT indépendante."
                ),
                severity="WARNING",
                evidence=[item],
            )
        )

    # ------------------------------------------------------------------
    # Historical QE
    # ------------------------------------------------------------------
    historical = [
        item for item in evidence
        if item.metadata.get("category") == "DFT_QE_HISTORICAL"
    ]

    if historical:
        findings.append(
            Finding(
                category="FACT",
                message=(
                    f"{subject}: {len(historical)} fichier(s) QE historique(s) "
                    "sont disponibles."
                ),
                severity="INFO",
                evidence=historical,
            )
        )

    # ------------------------------------------------------------------
    # New QE campaign
    # ------------------------------------------------------------------
    new_campaign = [
        item for item in evidence
        if item.metadata.get("category") == "DFT_QE_NEW_CAMPAIGN"
    ]

    if new_campaign:
        findings.append(
            Finding(
                category="FACT",
                message=(
                    f"{subject}: {len(new_campaign)} fichier(s) de la "
                    "nouvelle campagne QE sont disponibles."
                ),
                severity="INFO",
                evidence=new_campaign,
            )
        )

    # ------------------------------------------------------------------
    # Historical vs new campaign separation
    # ------------------------------------------------------------------
    if historical and new_campaign:
        findings.append(
            Finding(
                category="WARNING",
                message=(
                    f"{subject}: deux générations de données QE sont présentes "
                    "(historique et nouvelle campagne). AIDA les maintient "
                    "séparées et ne fusionne pas leurs résultats."
                ),
                severity="WARNING",
                evidence=historical[:1] + new_campaign[:1],
            )
        )

    # ------------------------------------------------------------------
    # Provenance sanity check
    # ------------------------------------------------------------------
    if "LITERATURE" not in categories:
        findings.append(
            Finding(
                category="WARNING",
                message=f"{subject}: aucune donnée LITERATURE identifiée.",
                severity="WARNING",
                evidence=[],
            )
        )

    if "COMPOSITE_SCREENING" in categories:
        findings.append(
            Finding(
                category="INTERPRETATION",
                message=(
                    f"{subject}: le score composite doit être interprété "
                    "comme un résultat de screening, distinct des résultats QE."
                ),
                severity="INFO",
                evidence=composite,
            )
        )

    return findings
