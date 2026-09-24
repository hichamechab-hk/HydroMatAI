#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path


PROJECT_ROOT = Path("/home/hk/HydroMatAI")

PRIORITY_CSV = PROJECT_ROOT / "reports" / "dft_h2_priority.csv"
PHASE55_CSV = (
    PROJECT_ROOT
    / "calculations"
    / "phase_55_final_scientific_consistency"
    / "phase55_final_ranking.csv"
)

HISTORICAL_ROOT = (
    PROJECT_ROOT / "calculations" / "top5_dft" / "TiFeH2"
)

CAMPAIGN_ROOT = (
    PROJECT_ROOT / "calculations" / "new_campaign" / "TiFeH2"
)


def read_csv_row(path: Path, material: str):
    if not path.exists():
        return None

    with path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        for row in rows:
            if (
                row.get("material") == material
                or row.get("name") == material
            ):
                return row

    return None


def extract_energy(path: Path):
    text = path.read_text(errors="replace")

    matches = re.findall(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        re.IGNORECASE,
    )

    if not matches:
        return None

    return float(matches[-1])


def scf_converged(path: Path):
    text = path.read_text(errors="replace")

    return bool(
        re.search(
            r"convergence has been achieved",
            text,
            re.IGNORECASE,
        )
    )


def collect_outs(root: Path):
    return sorted(root.rglob("*.out"))


def main():

    print("=" * 78)
    print("PHASE 12 — SCIENTIFIC STATUS LAYER")
    print("=" * 78)

    print("READ-ONLY")
    print("Aucun pw.x ne sera exécuté.")
    print("Aucune donnée scientifique ne sera modifiée.")
    print()

    material = "TiFeH2"

    # ------------------------------------------------------------------
    # 1. LITERATURE / SCREENING
    # ------------------------------------------------------------------

    print("=" * 78)
    print("1. LITERATURE / HYDROMATAI SCREENING")
    print("=" * 78)

    priority = read_csv_row(PRIORITY_CSV, material)
    phase55 = read_csv_row(PHASE55_CSV, material)

    if priority:
        print(f"H2 uptake            : {priority.get('h2_uptake_wt_percent')}")
        print(f"Ambient score        : {priority.get('ambient_score')}")
        print(f"Scientific score     : {priority.get('scientific_score')}")
        print(f"Confidence           : {priority.get('confidence')}")

    if phase55:
        print(
            f"Final screening score: "
            f"{phase55.get('final_screening_score')}"
        )

    print()
    print("[RULE]")
    print("Ces valeurs ne constituent pas une validation DFT indépendante.")

    # ------------------------------------------------------------------
    # 2. HISTORICAL QE
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("2. HISTORICAL QE")
    print("=" * 78)

    historical_outs = collect_outs(HISTORICAL_ROOT)

    historical_scf = []
    historical_electronic = []

    for path in historical_outs:

        name = path.name.lower()

        if "relax" in name or "_scf" in name:
            energy = extract_energy(path)
            converged = scf_converged(path)

            if energy is not None:
                historical_scf.append(
                    (
                        path,
                        energy,
                        converged,
                    )
                )

        if any(
            x in name
            for x in ("bands", "dos", "nscf")
        ):
            historical_electronic.append(path)

    for path, energy, converged in historical_scf:
        print(
            f"{path.name:35s} "
            f"energy={energy:.8f} Ry "
            f"SCF_CONVERGED={converged}"
        )

    print(
        f"\nHistorical electronic outputs: "
        f"{len(historical_electronic)}"
    )

    # ------------------------------------------------------------------
    # 3. NEW CAMPAIGN
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("3. NEW QE CAMPAIGN")
    print("=" * 78)

    campaign_outs = collect_outs(CAMPAIGN_ROOT)

    converged_count = 0

    for path in campaign_outs:

        energy = extract_energy(path)

        if energy is None:
            continue

        converged = scf_converged(path)

        if converged:
            converged_count += 1

        print(
            f"{path.name:45s} "
            f"energy={energy:.8f} Ry "
            f"SCF_CONVERGED={converged}"
        )

    print(
        f"\nCampaign SCF converged: "
        f"{converged_count}/{len(campaign_outs)}"
    )

    # ------------------------------------------------------------------
    # 4. NUMERICAL STABILITY
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("4. NUMERICAL STABILITY")
    print("=" * 78)

    cutoff_energy = [
        -880.83702817,
        -880.83529755,
        -880.82888145,
    ]

    kpoint_energy = [
        -880.83702817,
        -880.73746520,
        -880.72434343,
    ]

    smearing_energy = [
        -880.83722826,
        -880.83722441,
        -880.83717588,
        -880.83702817,
    ]

    cutoff_spread = max(cutoff_energy) - min(cutoff_energy)
    kpoint_spread = max(kpoint_energy) - min(kpoint_energy)
    smearing_spread = max(smearing_energy) - min(smearing_energy)

    tolerance = 1e-4

    print(
        f"ECUTWFC spread : {cutoff_spread:.8f} Ry "
        f"-> {'STABLE' if cutoff_spread <= tolerance else 'NOT_STABLE'}"
    )

    print(
        f"KPOINT spread  : {kpoint_spread:.8f} Ry "
        f"-> {'STABLE' if kpoint_spread <= tolerance else 'NOT_STABLE'}"
    )

    print(
        f"SMEARING spread : {smearing_spread:.8f} Ry "
        f"-> {'STABLE' if smearing_spread <= tolerance else 'NOT_STABLE'}"
    )

    numerical_stability = (
        cutoff_spread <= tolerance
        and kpoint_spread <= tolerance
        and smearing_spread <= tolerance
    )

    # ------------------------------------------------------------------
    # 5. SCIENTIFIC STATUS
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("5. AIDA SCIENTIFIC STATUS")
    print("=" * 78)

    if numerical_stability:
        status = "NUMERICAL_STABILITY_ESTABLISHED"
    else:
        status = "SCIENTIFIC_STATUS_NOT_ESTABLISHED"

    print(f"STATUS : {status}")

    print()
    print("INTERPRETATION:")
    print(
        "- Les calculs SCF individuels peuvent être convergés."
    )
    print(
        "- La stabilité numérique globale n'est pas établie."
    )
    print(
        "- Les sorties DOS/BANDS sont disponibles mais ne suffisent "
        "pas à établir une validation électronique."
    )
    print(
        "- Le score 0.991579 reste un score composite de screening."
    )
    print(
        "- La valeur H2 = 1.86 wt% reste une donnée de littérature."
    )
    print(
        "- Aucune de ces informations n'est convertie en "
        "'SCIENTIFICALLY_VALIDATED'."
    )

    # ------------------------------------------------------------------
    # 6. FINAL AIDA STATEMENT
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("6. FINAL AIDA STATEMENT")
    print("=" * 78)

    print(
        "TiFeH2 possède des calculs QE individuellement convergés "
        "et des sorties électroniques disponibles."
    )

    print(
        "Cependant, les séries cutoff, k-points et smearing "
        "ne démontrent pas actuellement une stabilité numérique "
        "selon la tolérance de 1e-4 Ry."
    )

    print(
        "AIDA ne considère donc pas le résultat comme "
        "scientifiquement validé sur la seule base de cette campagne."
    )

    print("\n" + "=" * 78)
    print("PHASE 12 TERMINÉE")
    print("=" * 78)


if __name__ == "__main__":
    main()
