from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Evidence
from .data_sources import collect_subject_sources


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_semantic_evidence(subject: str) -> list[Evidence]:
    """
    Convert existing HydroMatAI records into provenance-aware Evidence.

    READ-ONLY:
    - no scientific calculation
    - no QE execution
    - no modification of existing data
    """
    data = collect_subject_sources(subject)

    evidence: list[Evidence] = []

    priority = data.get("priority_report") or {}
    phase55 = data.get("phase55_ranking") or {}

    # Literature-derived H2 uptake
    h2 = _float(priority.get("h2_uptake_wt_percent"))
    if h2 is not None:
        evidence.append(
            Evidence(
                name="h2_uptake_wt_percent",
                value=h2,
                source="reports/dft_h2_priority.csv",
                status="OBSERVED",
                metadata={
                    "category": "LITERATURE",
                    "unit": "wt%",
                    "material": subject,
                    "field": "h2_uptake_wt_percent",
                },
            )
        )

    # Ambient score already produced by HydroMatAI
    ambient = _float(priority.get("ambient_score"))
    if ambient is not None:
        evidence.append(
            Evidence(
                name="ambient_score",
                value=ambient,
                source="reports/dft_h2_priority.csv",
                status="DERIVED",
                metadata={
                    "category": "HYDROMATAI_SCREENING",
                    "material": subject,
                    "field": "ambient_score",
                },
            )
        )

    # Scientific score
    scientific = _float(priority.get("scientific_score"))
    if scientific is not None:
        evidence.append(
            Evidence(
                name="scientific_score",
                value=scientific,
                source="reports/dft_h2_priority.csv",
                status="DERIVED",
                metadata={
                    "category": "HYDROMATAI_SCREENING",
                    "material": subject,
                    "field": "scientific_score",
                },
            )
        )

    # Final composite score: take it from Phase 55, never recompute it.
    final_score = _float(phase55.get("final_screening_score"))
    if final_score is not None:
        evidence.append(
            Evidence(
                name="final_screening_score",
                value=final_score,
                source=(
                    "calculations/phase_55_final_scientific_consistency/"
                    "phase55_final_ranking.csv"
                ),
                status="COMPOSITE",
                metadata={
                    "category": "COMPOSITE_SCREENING",
                    "material": subject,
                    "field": "final_screening_score",
                    "independent_dft_validation": False,
                },
            )
        )

    # Scientific corrected value from Phase 55.
    corrected = _float(phase55.get("scientific_corrected"))
    if corrected is not None:
        evidence.append(
            Evidence(
                name="scientific_corrected",
                value=corrected,
                source=(
                    "calculations/phase_55_final_scientific_consistency/"
                    "phase55_final_ranking.csv"
                ),
                status="DERIVED",
                metadata={
                    "category": "HYDROMATAI_SCREENING",
                    "material": subject,
                    "field": "scientific_corrected",
                },
            )
        )

    # QE provenance: files only, no interpretation of their contents yet.
    qe_files = data.get("qe_files", {})

    for path in qe_files.get("historical_top5_dft", []):
        evidence.append(
            Evidence(
                name="qe_historical_file",
                value=path,
                source=path,
                status="COMPUTED",
                metadata={
                    "category": "DFT_QE_HISTORICAL",
                    "material": subject,
                },
            )
        )

    for path in qe_files.get("new_campaign", []):
        evidence.append(
            Evidence(
                name="qe_new_campaign_file",
                value=path,
                source=path,
                status="COMPUTED",
                metadata={
                    "category": "DFT_QE_NEW_CAMPAIGN",
                    "material": subject,
                },
            )
        )

    return evidence
