from __future__ import annotations


def adsorption_energy(
    e_complex: float,
    e_host: float,
    e_h2: float,
) -> float:

    return e_complex - e_host - e_h2


def hydrogen_score(
    energy: float | None,
) -> float:

    if energy is None:
        return 0.0

    return max(
        0.0,
        min(
            1.0,
            abs(energy) / 0.5
        )
    )
