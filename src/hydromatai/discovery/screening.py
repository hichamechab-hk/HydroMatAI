from __future__ import annotations

from .candidate import MOFCandidate


def screen_candidate(
    candidate: MOFCandidate,
) -> bool:

    return (
        candidate.surface_area >= 1000
        and candidate.void_fraction >= 0.5
        and candidate.pld >= 3.0
        and candidate.lcd >= 6.0
    )


def screening_score(
    candidate: MOFCandidate,
) -> float:

    score = 0.0

    score += min(candidate.surface_area / 2000, 1.0)
    score += min(candidate.void_fraction, 1.0)
    score += min(candidate.pld / 10, 1.0)
    score += min(candidate.lcd / 20, 1.0)

    return score / 4
