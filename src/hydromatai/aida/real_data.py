from __future__ import annotations

import re
from pathlib import Path

from .scientific_status import NumericalEvidence, NumericalStatus
from hydromatai.dft.validation.kpoint_audit import parse_kpoint_output
from hydromatai.dft.validation.kpoint_analyzer import analyze_kpoint_convergence


PROJECT_ROOT = Path("/home/hk/HydroMatAI")

CAMPAIGN_DIR = (
    PROJECT_ROOT
    / "calculations/new_campaign/TiFeH2"
)

HISTORICAL_DIR = (
    PROJECT_ROOT
    / "calculations/top5_dft/TiFeH2"
)

THRESHOLD_RY = 1e-4


def _read(path: Path) -> str:
    return path.read_text(errors="replace")


def _energy(text: str) -> float | None:
    values = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        flags=re.IGNORECASE,
    )

    return float(values[-1]) if values else None


def _converged(text: str) -> bool:
    lowered = text.lower()

    return (
        "convergence has been achieved" in lowered
        or "convergence achieved" in lowered
    )


def _series_status(paths: list[Path]) -> NumericalStatus:
    energies = []

    for path in sorted(paths):
        value = _energy(_read(path))

        if value is not None:
            energies.append(value)

    if len(energies) < 2:
        return NumericalStatus.INSUFFICIENT

    spread = max(energies) - min(energies)

    if spread <= THRESHOLD_RY:
        return NumericalStatus.ESTABLISHED

    return NumericalStatus.NOT_ESTABLISHED


def _all_campaign_outputs() -> list[Path]:
    return sorted(CAMPAIGN_DIR.rglob("*.out"))


def _cutoff_outputs() -> list[Path]:
    return sorted(
        path
        for path in _all_campaign_outputs()
        if re.search(
            r"run_\d+Ry/TiFeH2_cutoff_\d+\.out$",
            str(path),
            flags=re.IGNORECASE,
        )
    )


def _kpoints_outputs() -> list[Path]:
    """
    Retourne exclusivement les sorties de la campagne k-points 140/560 Ry
    lorsqu'elle existe.

    Une ancienne campagne ne doit jamais être mélangée à la campagne
    scientifique actuelle.
    """
    return sorted(
        path
        for path in _all_campaign_outputs()
        if re.search(
            r"run_kpoints_\d+x\d+x\d+_140Ry/"
            r"TiFeH2_kpoints_\d+x\d+x\d+_140\.out$",
            str(path),
            flags=re.IGNORECASE,
        )
    )

def _kpoint_grid(path: Path) -> str:
    match = re.search(
        r"run_kpoints_(\d+x\d+x\d+)(?:_140Ry)?",
        str(path),
        re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            f"Grille k-points introuvable dans {path}"
        )

    return match.group(1)


def _kpoints_status(paths: list[Path]) -> NumericalStatus:
    results = [
        parse_kpoint_output(_kpoint_grid(path), path)
        for path in sorted(paths)
    ]

    report = analyze_kpoint_convergence(
        results,
        threshold_ry=THRESHOLD_RY,
    )

    if report.status == "INSUFFICIENT_DATA":
        return NumericalStatus.INSUFFICIENT

    if report.status == "NUMERICAL_STABILITY_ESTABLISHED":
        return NumericalStatus.ESTABLISHED

    return NumericalStatus.NOT_ESTABLISHED


def _smearing_outputs() -> list[Path]:
    return sorted(
        path
        for path in _all_campaign_outputs()
        if re.search(
            r"smearing_tests/degauss_"
            r"0\.\d+Ry/TiFeH2_degauss_0\.\d+Ry\.out$",
            str(path),
            flags=re.IGNORECASE,
        )
    )


def _historical_electronic_outputs_available() -> bool:
    patterns = (
        "*bands*.out",
        "*dos*.out",
        "*nscf*.out",
    )

    return any(
        any(HISTORICAL_DIR.rglob(pattern))
        for pattern in patterns
    )


def _campaign_scf_records() -> list[dict]:
    """
    Construit l'inventaire des sorties SCF de la campagne.

    Contrairement à l'ancienne version, les fichiers sans
    énergie totale ne sont plus silencieusement éliminés.

    Chaque sortie est conservée dans l'inventaire avec :
      - path
      - energy
      - converged
      - complete
    """

    records = []

    for path in _all_campaign_outputs():

        # Les fichiers kpoints_smearing_0.002Ry
        # sont des sorties auxiliaires et ne font pas partie
        # des trois séries principales.
        if "kpoints_smearing_0.002Ry" in str(path):
            continue

        text = _read(path)
        energy = _energy(text)

        records.append(
            {
                "path": path,
                "energy": energy,
                "converged": _converged(text),
                "complete": energy is not None,
            }
        )

    return records


def build_tifeh2_numerical_evidence() -> NumericalEvidence:
    """
    Construit l'evidence numerique réelle de la campagne TiFeH2.

    Les sorties sont comptées même lorsqu'elles sont incomplètes.

    Pour la campagne actuelle :
      - 15 sorties principales détectées
      - 13 avec énergie exploitable
      - 13 convergées
      - 2 incomplètes
    """

    cutoff = _cutoff_outputs()
    kpoints = _kpoints_outputs()
    smearing = _smearing_outputs()

    scf_records = _campaign_scf_records()

    scf_total = len(scf_records)

    scf_converged = sum(
        1
        for record in scf_records
        if record["complete"] and record["converged"]
    )

    scf_incomplete = sum(
        1
        for record in scf_records
        if not record["complete"]
    )

    return NumericalEvidence(
        scf_converged=scf_converged,
        scf_total=scf_total,
        scf_incomplete=scf_incomplete,
        cutoff_status=_series_status(cutoff),
        kpoints_status=_kpoints_status(kpoints),
        smearing_status=_series_status(smearing),
        electronic_outputs_available=(
            _historical_electronic_outputs_available()
        ),
    )
