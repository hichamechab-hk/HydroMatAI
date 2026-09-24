from .models import AIDAResult


def render_report(result: AIDAResult) -> str:
    lines = [
        "=" * 70,
        "AIDA SCIENTIFIC ANALYSIS",
        "=" * 70,
        f"Subject: {result.subject}",
        "",
        "FINDINGS",
        "-" * 70,
    ]

    if result.findings:
        for finding in result.findings:
            lines.append(
                f"[{finding.severity}] "
                f"{finding.category}: {finding.message}"
            )
    else:
        lines.append("No findings.")

    if result.metadata.get("scientific_status"):
        lines.extend([
            "",
            "SCIENTIFIC STATUS",
            "-" * 70,
            f"Status: {result.metadata['scientific_status']}",
        ])

        if result.metadata.get("numerical_stability"):
            lines.append(
                "Numerical stability: "
                f"{result.metadata['numerical_stability']}"
            )

        if result.metadata.get("scientific_status_reason"):
            lines.append(
                "Reason: "
                f"{result.metadata['scientific_status_reason']}"
            )

    if result.warnings:
        lines.extend([
            "",
            "WARNINGS",
            "-" * 70,
        ])
        lines.extend(f"- {warning}" for warning in result.warnings)

    return "\n".join(lines)
