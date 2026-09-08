from __future__ import annotations
"""Models for published scientific results."""


from dataclasses import dataclass, field
from typing import Any


def infer_material_family(material: str) -> str:
    """Infer a broad material family from its name."""

    name = material.strip().lower()

    # Explicit hybrid/material-mixture patterns first.
    hybrid_prefixes = (
        "mgh2-",
        "mg2feh",
        "mg2nih",
    )

    hybrid_markers = (
        "/",
        "lialh4",
        "libh4",
        "linh2",
        "nah2",
        "mg(nh",
    )

    if (
        name.startswith(hybrid_prefixes)
        or any(marker in name for marker in hybrid_markers)
    ):
        return "HYBRID"

    # Common MOF nomenclature.
    mof_prefixes = (
        "mof-",
        "mof_",
        "irmof-",
        "uio-",
        "mil-",
        "dut-",
        "nu-",
        "hkust-",
        "juc-",
        "dmodf-",
        "moc-",
        "fji-",
        "pcn-",
        "zif-",
        "bio-mof",
    )

    if name.startswith(mof_prefixes):
        return "MOF"

    # Common MOF names that do not necessarily use a prefix.
    mof_names = {
        "hkust-1",
        "cubic mofs",
    }

    if name in mof_names:
        return "MOF"

    # Conventional hydrides.
    hydride_markers = (
        "mgh2",
        "naalh4",
        "nah4",
        "alh3",
        "lialh4",
        "libh4",
        "lanih",
        "fetih",
        "mgh",
        "mg2nih",
        "mg2feh",
    )

    if any(marker in name for marker in hydride_markers):
        return "HYDRIDE"

    return "OTHER"


@dataclass
class LiteratureResult:
    """A scientific result extracted from a published source."""

    material: str
    property_name: str
    value: float
    unit: str

    source_type: str = "literature"
    family: str | None = None

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    doi: str | None = None

    method: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None

    def __post_init__(self) -> None:
        self.material = self.material.strip()
        self.property_name = self.property_name.strip()
        self.unit = self.unit.strip()

        if not self.material:
            raise ValueError("material cannot be empty")

        if not self.property_name:
            raise ValueError("property_name cannot be empty")

        if not self.unit:
            raise ValueError("unit cannot be empty")

        if self.source_type != "literature":
            raise ValueError("source_type must be 'literature'")

        if self.family is None:
            self.family = infer_material_family(self.material)

        self.family = self.family.strip().upper()

        if self.family not in {
            "MOF",
            "HYDRIDE",
            "HYBRID",
            "OTHER",
        }:
            raise ValueError(
                "family must be MOF, HYDRIDE, HYBRID or OTHER"
            )

        if self.year is not None and not 1800 <= self.year <= 2100:
            raise ValueError("year must be between 1800 and 2100")

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return {
            "material": self.material,
            "property_name": self.property_name,
            "value": self.value,
            "unit": self.unit,
            "source_type": self.source_type,
            "family": self.family,
            "title": self.title,
            "authors": list(self.authors),
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "method": self.method,
            "conditions": dict(self.conditions),
            "notes": self.notes,
        }
