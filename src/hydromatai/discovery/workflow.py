from __future__ import annotations

from .candidate import MOFCandidate
from .screening import screening_score


def evaluate_candidate(
    candidate: MOFCandidate,
):

    candidate.score = screening_score(candidate)

    return candidate
