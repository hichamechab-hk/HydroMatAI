from pathlib import Path
from typing import Any

from .models import Evidence


def evidence(
    name: str,
    value: Any,
    source: str | Path,
    status: str = "OBSERVED",
    **metadata: Any,
) -> Evidence:
    return Evidence(
        name=name,
        value=value,
        source=str(source),
        status=status,
        metadata=metadata,
    )


def classify_source(source: str | Path) -> str:
    path = str(source).lower()

    if "literature" in path or "reference" in path:
        return "LITERATURE"

    if "qe" in path or "quantum" in path or "pw." in path:
        return "DFT_QE"

    if "screen" in path or "ranking" in path or "score" in path:
        return "HYDROMATAI_SCREENING"

    return "UNKNOWN"
