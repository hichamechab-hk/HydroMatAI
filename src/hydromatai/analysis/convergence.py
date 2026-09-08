from __future__ import annotations
"""Convergence analysis for QE calculations."""


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
