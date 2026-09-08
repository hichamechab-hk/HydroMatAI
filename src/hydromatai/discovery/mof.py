from __future__ import annotations
"""Adapters between MOFX-DB records and HydroMatAI candidates."""


from .candidate import MOFCandidate
from .database import MOFRecord


def record_to_candidate(
    record: MOFRecord,
) -> MOFCandidate:

    return MOFCandidate(
        name=record.name,
        cif_path=record.cif_path,
        surface_area=record.surface_area or 0.0,
        void_fraction=record.void_fraction or 0.0,
        pld=record.pld or 0.0,
        lcd=record.lcd or 0.0,
    )
