#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path
from statistics import mean


PROJECT_ROOT = Path("/home/hk/HydroMatAI")
CAMPAIGN_ROOT = PROJECT_ROOT / "calculations" / "new_campaign" / "TiFeH2"
HISTORICAL_ROOT = PROJECT_ROOT / "calculations" / "top5_dft" / "TiFeH2"

ENERGY_TOL_RY = 1e-4


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def extract_energy(text: str):
    matches = re.findall(
        r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?)\s+Ry",
        text,
        re.IGNORECASE,
    )
    if not matches:
        return None
    return float(matches[-1])


def extract_fermi(text: str):
    matches = re.findall(
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
        text,
        re.IGNORECASE,
    )
    if not matches:
        matches = re.findall(
            r"EFermi\s*=\s*([-+]?\d+(?:\.\d+)?)\s*eV",
            text,
            re.IGNORECASE,
        )
    if not matches:
        return None
    return float(matches[-1])


def extract_iterations(text: str):
    matches = re.findall(
        r"convergence has been achieved in\s+(\d+)\s+iterations",
        text,
        re.IGNORECASE,
    )
    if not matches:
        return None
    return int(matches[-1])


def scf_converged(text: str) -> bool:
    return bool(
        re.search(
            r"convergence has been achieved",
            text,
            re.IGNORECASE,
        )
    )


def classify_output(path: Path):
    text = read_text(path)

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "energy_ry": extract_energy(text),
        "fermi_ev": extract_fermi(text),
        "iterations": extract_iterations(text),
        "scf_converged": scf_converged(text),
    }


def find_outputs(root: Path):
    return sorted(root.rglob("*.out"))


def print_record(label, record):
    print(f"\n[{label}]")
    print(f"file        : {record['file']}")
    print(f"energy      : {record['energy_ry']}")
    print(f"fermi       : {record['fermi_ev']}")
    print(f"iterations  : {record['iterations']}")
    print(f"scf         : {record['scf_converged']}")


def evaluate_series(name, records, reference_label=None):
    print("\n" + "=" * 78)
    print(f"SERIES : {name}")
    print("=" * 78)

    valid = [r for r in records if r["energy_ry"] is not None]

    if len(valid) < 2:
        print("[INSUFFICIENT_EVIDENCE] moins de 2 energies exploitables")
        return {
            "series": name,
            "status": "INSUFFICIENT_EVIDENCE",
            "spread_ry": None,
        }

    for r in valid:
        print(
            f"{r['label']:>12} : "
            f"{r['energy_ry']:.8f} Ry"
        )

    if reference_label is not None:
        ref = next(
            (r for r in valid if r["label"] == reference_label),
            None,
        )
    else:
        ref = valid[-1]

    if ref is None:
        print("[INSUFFICIENT_EVIDENCE] reference absente")
        return {
            "series": name,
            "status": "INSUFFICIENT_EVIDENCE",
            "spread_ry": None,
        }

    reference_energy = ref["energy_ry"]

    deltas = []
    for r in valid:
        delta = r["energy_ry"] - reference_energy
        deltas.append(abs(delta))
        print(
            f"delta({r['label']},{ref['label']}) = "
            f"{delta:+.8f} Ry"
        )

    spread = max(r["energy_ry"] for r in valid) - min(
        r["energy_ry"] for r in valid
    )

    print(f"spread      : {spread:.8f} Ry")
    print(f"tolérance   : {ENERGY_TOL_RY:.8f} Ry")

    if spread <= ENERGY_TOL_RY:
        status = "NUMERICAL_STABILITY_ESTABLISHED"
        print("[OK] stabilité numérique établie pour cette série")
    else:
        status = "NUMERICAL_STABILITY_NOT_ESTABLISHED"
        print("[WARNING] stabilité numérique non établie")

    return {
        "series": name,
        "status": status,
        "spread_ry": spread,
    }


def main():
    print("=" * 78)
    print("PHASE 11 — EVALUATION DE LA STABILITE NUMERIQUE")
    print("=" * 78)
    print("READ-ONLY")
    print("Aucun pw.x ne sera execute.")
    print("Aucune donnée scientifique ne sera modifiée.")
    print()

    historical = find_outputs(HISTORICAL_ROOT)
    campaign = find_outputs(CAMPAIGN_ROOT)

    print(f"[INFO] OUT historiques : {len(historical)}")
    print(f"[INFO] OUT campagne    : {len(campaign)}")

    # ------------------------------------------------------------------
    # 1. INDIVIDUAL SCF CONVERGENCE
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("1. CONVERGENCE INDIVIDUELLE")
    print("=" * 78)

    for path in historical:
        record = classify_output(path)
        if record["energy_ry"] is not None:
            print_record("HISTORICAL", record)

    for path in campaign:
        record = classify_output(path)
        if record["energy_ry"] is not None:
            print_record("NEW_CAMPAIGN", record)

    # ------------------------------------------------------------------
    # 2. CUTOFF
    # ------------------------------------------------------------------

    cutoff = []

    for path in campaign:
        m = re.search(r"cutoff_(\d+)\.out$", path.name)
        if not m:
            continue

        record = classify_output(path)
        if record["energy_ry"] is not None:
            cutoff.append(
                {
                    **record,
                    "label": m.group(1),
                }
            )

    cutoff.sort(key=lambda x: int(x["label"]))

    cutoff_result = evaluate_series(
        "ECUTWFC",
        cutoff,
        reference_label="100",
    )

    # ------------------------------------------------------------------
    # 3. K-POINTS
    # ------------------------------------------------------------------

    kpoints = []

    for path in campaign:
        m = re.search(r"kpoints_(\d+)\.out$", path.name)
        if not m:
            continue

        record = classify_output(path)

        if record["energy_ry"] is not None:
            label = f"{m.group(1)}x{m.group(1)}x{m.group(1)}"
            kpoints.append(
                {
                    **record,
                    "label": label,
                }
            )

    def kp_key(x):
        return int(x["label"].split("x")[0])

    kpoints.sort(key=kp_key)

    kpoints_result = evaluate_series(
        "K-POINTS",
        kpoints,
        reference_label="4x4x4",
    )

    # ------------------------------------------------------------------
    # 4. SMEARING
    # ------------------------------------------------------------------

    smearing = []

    for path in campaign:
        m = re.search(r"degauss_(0\.\d+)Ry\.out$", path.name)
        if not m:
            continue

        record = classify_output(path)

        if record["energy_ry"] is not None:
            smearing.append(
                {
                    **record,
                    "label": m.group(1),
                }
            )

    smearing.sort(key=lambda x: float(x["label"]))

    smearing_result = evaluate_series(
        "SMEARING",
        smearing,
        reference_label="0.005",
    )

    # ------------------------------------------------------------------
    # 5. ELECTRONIC OUTPUTS
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("5. BAND / DOS / NSCF")
    print("=" * 78)

    electronic = []

    for path in historical + campaign:
        name = path.name.lower()

        if any(
            token in name
            for token in ("bands", "dos", "nscf")
        ):
            electronic.append(path)

    if electronic:
        for path in electronic:
            print(f"[AVAILABLE] {path.relative_to(PROJECT_ROOT)}")

        electronic_status = "ELECTRONIC_OUTPUTS_AVAILABLE"
    else:
        print("[INSUFFICIENT_EVIDENCE] aucun output électronique")
        electronic_status = "INSUFFICIENT_EVIDENCE"

    # ------------------------------------------------------------------
    # 6. FINAL INTERPRETATION
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("6. INTERPRETATION AIDA")
    print("=" * 78)

    print(
        "\n[IMPORTANT] Une convergence SCF individuelle ne signifie "
        "pas validation scientifique."
    )

    print(
        "[IMPORTANT] Une série dont l'énergie varie au-delà de la "
        "tolérance ne permet pas d'établir la stabilité numérique."
    )

    print(
        "[IMPORTANT] DOS/BANDS/NSCF disponibles != validation "
        "électronique automatique."
    )

    series_results = [
        cutoff_result,
        kpoints_result,
        smearing_result,
    ]

    stable_count = sum(
        r["status"] == "NUMERICAL_STABILITY_ESTABLISHED"
        for r in series_results
    )

    unstable_count = sum(
        r["status"] == "NUMERICAL_STABILITY_NOT_ESTABLISHED"
        for r in series_results
    )

    insufficient_count = sum(
        r["status"] == "INSUFFICIENT_EVIDENCE"
        for r in series_results
    )

    print(f"\nSéries stables       : {stable_count}/3")
    print(f"Séries non stables   : {unstable_count}/3")
    print(f"Séries insuffisantes : {insufficient_count}/3")

    if unstable_count == 0 and insufficient_count == 0:
        global_status = "NUMERICAL_STABILITY_ESTABLISHED"
    elif insufficient_count > 0:
        global_status = "INSUFFICIENT_EVIDENCE"
    else:
        global_status = "NUMERICAL_STABILITY_NOT_ESTABLISHED"

    print(f"\nSTATUS GLOBAL : {global_status}")

    print("\nSTATUTS AUTORISÉS PAR CETTE PHASE :")
    print("  - NUMERICAL_STABILITY_ESTABLISHED")
    print("  - NUMERICAL_STABILITY_NOT_ESTABLISHED")
    print("  - INSUFFICIENT_EVIDENCE")
    print("  - ELECTRONIC_OUTPUTS_AVAILABLE")

    print(
        "\nAIDA NE CONVERTIT AUCUN DE CES STATUTS EN "
        "'SCIENTIFICALLY_VALIDATED'."
    )

    print("\n" + "=" * 78)
    print("PHASE 11 TERMINÉE")
    print("=" * 78)


if __name__ == "__main__":
    main()
