"""Scientific analysis utilities for HydroMatAI."""

from .analysis import analyze_material
from .evaluation import (
    ScientificEvaluation,
    evaluate_result,
    evaluate_results,
)
from .report import write_scientific_report
from .workflow import ScientificWorkflow

__all__ = [
    "ScientificEvaluation",
    "ScientificWorkflow",
    "analyze_material",
    "evaluate_result",
    "evaluate_results",
    "write_scientific_report",
]
