from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    name: str
    value: Any
    source: str
    status: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    category: str
    message: str
    severity: str = "INFO"
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class AIDAResult:
    subject: str
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
