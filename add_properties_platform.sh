#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================
# HydroMatAI - Electronic + Optical Properties Platform
# ============================================================
# Ajoute :
#   - Electronic properties
#   - DOS / PDOS parsers
#   - Band structure parser
#   - Optical properties parser
#   - Automatic plots
#   - Automatic interpretation
#   - Automatic report generation
#
# IMPORTANT :
#   - Ne lance aucun calcul Quantum ESPRESSO
#   - Ne supprime aucun fichier existant
#   - Ne modifie pas les calculs actuellement en cours
# ============================================================

PROJECT="${HOME}/HydroMatAI"
SRC="${PROJECT}/src/hydromatai"

echo
echo "============================================================"
echo " HydroMatAI - ELECTRONIC + OPTICAL PLATFORM"
echo "============================================================"
echo

cd "$PROJECT"

mkdir -p \
    "$SRC/properties/electronic" \
    "$SRC/properties/optical" \
    "$SRC/analysis" \
    "$SRC/visualization" \
    "$SRC/reports"

# ============================================================
# ELECTRONIC PROPERTIES
# ============================================================

cat > "$SRC/properties/electronic/dos.py" <<'PY'
"""Density of States utilities for Quantum ESPRESSO outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class DOSData:
    energy: list[float]
    values: list[float]
    fermi_energy: float | None = None


def read_fermi_energy(text: str) -> float | None:
    patterns = [
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        r"highest occupied level.*?([-+0-9.EeDd]+)\s+ev",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).replace("D", "E").replace("d", "e")
            return float(value)

    return None


def parse_dos_file(path: str | Path) -> DOSData:
    path = Path(path)

    energies = []
    values = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                if len(parts) >= 2:
                    energies.append(float(parts[0]))
                    values.append(float(parts[1]))
            except ValueError:
                continue

    return DOSData(
        energy=energies,
        values=values,
    )


def find_band_gap(
    energy: list[float],
    dos: list[float],
    threshold: float = 1e-8,
) -> float | None:
    """Estimate a DOS gap around zero energy.

    Assumes the energy axis has already been shifted so that
    the Fermi level is approximately zero.
    """

    if not energy or not dos:
        return None

    occupied = [
        e for e, d in zip(energy, dos)
        if e <= 0.0 and abs(d) > threshold
    ]

    unoccupied = [
        e for e, d in zip(energy, dos)
        if e >= 0.0 and abs(d) > threshold
    ]

    if not occupied or not unoccupied:
        return None

    return max(0.0, min(unoccupied) - max(occupied))
PY

# ============================================================
# BAND STRUCTURE
# ============================================================

cat > "$SRC/properties/electronic/bands.py" <<'PY'
"""Band-structure data handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BandData:
    kpoints: list[float]
    bands: list[list[float]]
    fermi_energy: float | None = None


def read_band_data(path: str | Path) -> BandData:
    """Read a simple whitespace-separated band data file.

    Expected format:
        k  band1  band2  band3 ...

    Blank lines are ignored.
    """

    path = Path(path)

    kpoints = []
    rows = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                values = [float(x) for x in parts]
            except ValueError:
                continue

            if len(values) >= 2:
                kpoints.append(values[0])
                rows.append(values[1:])

    if not rows:
        return BandData([], [])

    number_of_bands = max(len(row) for row in rows)

    bands = [
        [
            row[i] if i < len(row) else float("nan")
            for row in rows
        ]
        for i in range(number_of_bands)
    ]

    return BandData(
        kpoints=kpoints,
        bands=bands,
    )


def estimate_band_gap(
    bands: list[list[float]],
    fermi_energy: float = 0.0,
) -> float | None:
    """Estimate a band gap relative to a supplied Fermi level."""

    if not bands:
        return None

    occupied_max = None
    unoccupied_min = None

    for band in bands:
        for energy in band:
            if energy <= fermi_energy:
                occupied_max = (
                    energy
                    if occupied_max is None
                    else max(occupied_max, energy)
                )

            if energy >= fermi_energy:
                unoccupied_min = (
                    energy
                    if unoccupied_min is None
                    else min(unoccupied_min, energy)
                )

    if occupied_max is None or unoccupied_min is None:
        return None

    return max(0.0, unoccupied_min - occupied_max)
PY

# ============================================================
# ELECTRONIC ANALYZER
# ============================================================

cat > "$SRC/properties/electronic/analyzer.py" <<'PY'
"""Automatic electronic-property interpretation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ElectronicInterpretation:
    classification: str
    band_gap: float | None
    explanation: str


def interpret_band_gap(band_gap: float | None) -> ElectronicInterpretation:

    if band_gap is None:
        return ElectronicInterpretation(
            classification="unknown",
            band_gap=None,
            explanation=(
                "Le gap électronique n'a pas pu être déterminé "
                "à partir des données disponibles."
            ),
        )

    if band_gap <= 0.05:
        classification = "metallic_or_semimetallic"
        explanation = (
            f"Le gap estimé est très faible ({band_gap:.4f} eV). "
            "Le système présente un comportement métallique ou "
            "semi-métallique selon la précision du calcul."
        )

    elif band_gap < 3.0:
        classification = "semiconductor"
        explanation = (
            f"Le gap électronique estimé est de {band_gap:.4f} eV. "
            "Le matériau est compatible avec un comportement "
            "semi-conducteur."
        )

    else:
        classification = "insulator"
        explanation = (
            f"Le gap électronique estimé est de {band_gap:.4f} eV. "
            "Le matériau présente un comportement de type isolant."
        )

    return ElectronicInterpretation(
        classification=classification,
        band_gap=band_gap,
        explanation=explanation,
    )
PY

# ============================================================
# OPTICAL PROPERTIES
# ============================================================

cat > "$SRC/properties/optical/dielectric.py" <<'PY'
"""Optical dielectric-function utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math


@dataclass
class DielectricData:
    energy: list[float]
    epsilon_real: list[float]
    epsilon_imag: list[float]


def read_dielectric_file(path: str | Path) -> DielectricData:
    """Read optical data.

    Expected columns:
        energy  epsilon_real  epsilon_imag
    """

    path = Path(path)

    energy = []
    real = []
    imag = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            try:
                if len(parts) >= 3:
                    energy.append(float(parts[0]))
                    real.append(float(parts[1]))
                    imag.append(float(parts[2]))
            except ValueError:
                continue

    return DielectricData(
        energy=energy,
        epsilon_real=real,
        epsilon_imag=imag,
    )


def refractive_index(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    magnitude = math.sqrt(
        epsilon_real ** 2 +
        epsilon_imag ** 2
    )

    return math.sqrt(
        max(0.0, (magnitude + epsilon_real) / 2.0)
    )


def extinction_coefficient(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:
    magnitude = math.sqrt(
        epsilon_real ** 2 +
        epsilon_imag ** 2
    )

    return math.sqrt(
        max(0.0, (magnitude - epsilon_real) / 2.0)
    )


def reflectivity(
    epsilon_real: float,
    epsilon_imag: float,
) -> float:

    n = refractive_index(
        epsilon_real,
        epsilon_imag,
    )

    k = extinction_coefficient(
        epsilon_real,
        epsilon_imag,
    )

    numerator = (n - 1.0) ** 2 + k ** 2
    denominator = (n + 1.0) ** 2 + k ** 2

    if denominator == 0:
        return 0.0

    return numerator / denominator
PY

cat > "$SRC/properties/optical/optical.py" <<'PY'
"""Automatic optical-property calculations."""

from __future__ import annotations

from .dielectric import (
    DielectricData,
    refractive_index,
    extinction_coefficient,
    reflectivity,
)


def calculate_optical_properties(
    data: DielectricData,
) -> dict[str, list[float]]:

    n = []
    k = []
    r = []

    for er, ei in zip(
        data.epsilon_real,
        data.epsilon_imag,
    ):

        n.append(
            refractive_index(er, ei)
        )

        k.append(
            extinction_coefficient(er, ei)
        )

        r.append(
            reflectivity(er, ei)
        )

    return {
        "energy": data.energy,
        "epsilon_real": data.epsilon_real,
        "epsilon_imag": data.epsilon_imag,
        "refractive_index": n,
        "extinction_coefficient": k,
        "reflectivity": r,
    }
PY

cat > "$SRC/properties/optical/analyzer.py" <<'PY'
"""Automatic interpretation of optical spectra."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OpticalInterpretation:
    absorption_peak_energy: float | None
    dielectric_peak_energy: float | None
    explanation: str


def interpret_optical_data(
    energy: list[float],
    epsilon_imag: list[float],
) -> OpticalInterpretation:

    if not energy or not epsilon_imag:
        return OpticalInterpretation(
            None,
            None,
            "Données optiques insuffisantes pour produire une interprétation.",
        )

    index = max(
        range(len(epsilon_imag)),
        key=lambda i: abs(epsilon_imag[i]),
    )

    peak_energy = energy[index]

    return OpticalInterpretation(
        absorption_peak_energy=peak_energy,
        dielectric_peak_energy=peak_energy,
        explanation=(
            "Le maximum de la partie imaginaire de la fonction "
            "diélectrique indique une région de forte réponse "
            "électronique aux excitations optiques. "
            f"Le maximum détecté se situe autour de "
            f"{peak_energy:.4f} eV."
        ),
    )
PY

# ============================================================
# ANALYSIS
# ============================================================

cat > "$SRC/analysis/convergence.py" <<'PY'
"""Convergence analysis for QE calculations."""

from __future__ import annotations

from pathlib import Path
import re


def extract_scf_energies(path: str | Path) -> list[float]:
    path = Path(path)

    pattern = re.compile(
        r"total energy\s*=\s*([-+0-9.EeDd]+)\s+Ry",
        re.IGNORECASE,
    )

    energies = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            match = pattern.search(line)

            if match:
                value = match.group(1)
                value = value.replace("D", "E").replace("d", "e")

                try:
                    energies.append(float(value))
                except ValueError:
                    pass

    return energies


def convergence_summary(path: str | Path) -> dict:
    energies = extract_scf_energies(path)

    result = {
        "iterations": len(energies),
        "initial_energy_Ry": None,
        "final_energy_Ry": None,
        "energy_change_Ry": None,
    }

    if energies:
        result["initial_energy_Ry"] = energies[0]
        result["final_energy_Ry"] = energies[-1]

    if len(energies) >= 2:
        result["energy_change_Ry"] = (
            energies[-1] - energies[0]
        )

    return result
PY

cat > "$SRC/analysis/interpretation.py" <<'PY'
"""General automatic interpretation engine."""


def interpret_convergence(summary: dict) -> str:

    iterations = summary.get("iterations", 0)

    if iterations == 0:
        return "Aucune énergie SCF détectée."

    if iterations < 10:
        return (
            f"La convergence SCF est rapide ({iterations} itérations "
            "détectées)."
        )

    if iterations < 40:
        return (
            f"La convergence SCF est raisonnable, avec "
            f"{iterations} itérations."
        )

    return (
        f"La convergence SCF est relativement lente "
        f"({iterations} itérations). Une optimisation du mélange "
        "électronique peut être envisagée."
    )
PY

# ============================================================
# VISUALIZATION
# ============================================================

cat > "$SRC/visualization/electronic_plots.py" <<'PY'
"""Automatic electronic-property plots."""

from __future__ import annotations

from pathlib import Path


def plot_dos(
    energy,
    dos,
    output: str | Path,
    fermi_energy: float = 0.0,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(energy, dos)
    plt.axvline(
        fermi_energy,
        linestyle="--",
        label="Fermi level",
    )

    plt.xlabel("Energy (eV)")
    plt.ylabel("DOS")
    plt.title("Density of States")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()


def plot_bands(
    kpoints,
    bands,
    output: str | Path,
    fermi_energy: float = 0.0,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))

    for band in bands:
        plt.plot(kpoints, band)

    plt.axhline(
        fermi_energy,
        linestyle="--",
        label="Fermi level",
    )

    plt.xlabel("k-path")
    plt.ylabel("Energy (eV)")
    plt.title("Electronic Band Structure")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()
PY

cat > "$SRC/visualization/optical_plots.py" <<'PY'
"""Automatic optical-property plots."""

from __future__ import annotations

from pathlib import Path


def plot_dielectric(
    energy,
    epsilon_real,
    epsilon_imag,
    output: str | Path,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))

    plt.plot(
        energy,
        epsilon_real,
        label="ε1",
    )

    plt.plot(
        energy,
        epsilon_imag,
        label="ε2",
    )

    plt.xlabel("Photon energy (eV)")
    plt.ylabel("Dielectric function")
    plt.title("Optical Dielectric Function")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()


def plot_reflectivity(
    energy,
    reflectivity,
    output: str | Path,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(energy, reflectivity)

    plt.xlabel("Photon energy (eV)")
    plt.ylabel("Reflectivity")
    plt.title("Optical Reflectivity")
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()
PY

# ============================================================
# REPORT GENERATOR
# ============================================================

cat > "$SRC/reports/property_report.py" <<'PY'
"""Automatic scientific report generation."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime


def create_report(
    output: str | Path,
    title: str = "HydroMatAI - Electronic and Optical Properties",
    electronic_text: str = "",
    optical_text: str = "",
    convergence_text: str = "",
):

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
{title}
============================================================

Generated by HydroMatAI
Date: {datetime.now().isoformat(timespec="seconds")}

1. ELECTRONIC PROPERTIES
------------------------------------------------------------

{electronic_text}

2. OPTICAL PROPERTIES
------------------------------------------------------------

{optical_text}

3. CONVERGENCE ANALYSIS
------------------------------------------------------------

{convergence_text}

4. SCIENTIFIC INTERPRETATION
------------------------------------------------------------

Electronic properties describe the electronic structure,
density of states and band-gap behaviour.

Optical properties describe the response of the material
to electromagnetic excitation through the dielectric
function, refractive index, extinction coefficient and
reflectivity.

These interpretations must be associated with the
corresponding Quantum ESPRESSO calculation parameters
and convergence criteria before publication.

============================================================
"""

    output.write_text(
        text.strip() + "\n",
        encoding="utf-8",
    )

    return output
PY

# ============================================================
# INIT FILES
# ============================================================

cat > "$SRC/properties/electronic/__init__.py" <<'PY'
"""Electronic properties."""

from .dos import DOSData, parse_dos_file, find_band_gap
from .bands import BandData, read_band_data, estimate_band_gap
from .analyzer import ElectronicInterpretation, interpret_band_gap

__all__ = [
    "DOSData",
    "parse_dos_file",
    "find_band_gap",
    "BandData",
    "read_band_data",
    "estimate_band_gap",
    "ElectronicInterpretation",
    "interpret_band_gap",
]
PY

cat > "$SRC/properties/optical/__init__.py" <<'PY'
"""Optical properties."""

from .dielectric import (
    DielectricData,
    read_dielectric_file,
    refractive_index,
    extinction_coefficient,
    reflectivity,
)

from .optical import calculate_optical_properties
from .analyzer import OpticalInterpretation, interpret_optical_data

__all__ = [
    "DielectricData",
    "read_dielectric_file",
    "refractive_index",
    "extinction_coefficient",
    "reflectivity",
    "calculate_optical_properties",
    "OpticalInterpretation",
    "interpret_optical_data",
]
PY

# ============================================================
# TEST
# ============================================================

echo
echo "------------------------------------------------------------"
echo "VERIFICATION"
echo "------------------------------------------------------------"

if [[ -x "${PROJECT}/.venv/bin/python" ]]; then

    "${PROJECT}/.venv/bin/python" - <<'PY'
from hydromatai.properties.electronic import (
    interpret_band_gap,
)

from hydromatai.properties.optical import (
    refractive_index,
    extinction_coefficient,
    reflectivity,
)

print("[OK] Electronic properties import")
print("[OK] Optical properties import")

result = interpret_band_gap(1.5)

print("[OK] Electronic interpretation:")
print(result.explanation)

n = refractive_index(4.0, 1.0)
k = extinction_coefficient(4.0, 1.0)
r = reflectivity(4.0, 1.0)

print("[OK] Optical calculation:")
print("     n =", n)
print("     k =", k)
print("     R =", r)
PY

else

    echo "AVERTISSEMENT : environnement Python non trouvé."

fi

# ============================================================
# GIT STATUS
# ============================================================

echo
echo "------------------------------------------------------------"
echo "FICHIERS AJOUTÉS"
echo "------------------------------------------------------------"

git status --short || true

echo
echo "============================================================"
echo " PLATFORME ELECTRONIC + OPTICAL INSTALLÉE"
echo "============================================================"
echo
echo "Aucun calcul Quantum ESPRESSO n'a été lancé."
echo
echo "Le calcul C_H2_d2p00_fixed.in peut continuer."
echo
