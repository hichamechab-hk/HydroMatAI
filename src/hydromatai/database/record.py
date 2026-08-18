from dataclasses import dataclass, field
from datetime import datetime, UTC

from hydromatai.dft import DFTResult


@dataclass
class MaterialRecord:
    """
    Enregistrement complet d'un matériau dans HydroMatAI.
    """

    formula: str
    name: str | None = None

    dft_result: DFTResult | None = None

    metadata: dict = field(default_factory=dict)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
