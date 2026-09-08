from __future__ import annotations
import os
os.system("clear")

import csv
from pathlib import Path


ROOT = Path("MOF_Library/MOFXDB_FULL")
CIF_DIR = ROOT / "cif"
METADATA = ROOT / "metadata.csv"

REPORTS = Path("reports/mofxdb_screening")
REPORTS.mkdir(parents=True, exist_ok=True)

TOP100 = REPORTS / "TOP100_H2.csv"
TOP20 = REPORTS / "TOP20_H2.csv"
DFT_PRIORITY = REPORTS / "dft_priority.csv"


def number(value: str | None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_vf(vf: float) -> float:
    return clamp(vf / 0.50, 0.0, 1.0)


def score_sa(sa: float) -> float:
    return clamp(sa / 1000.0, 0.0, 1.0)


def score_pld(pld: float) -> float:
    return clamp(pld / 3.0, 0.0, 1.0)


def score_lcd(lcd: float) -> float:
    return clamp(lcd / 6.0, 0.0, 1.0)


def score_global(
    vf: float,
    sa: float,
    pld: float,
    lcd: float,
) -> float:
    return (
        0.35 * score_vf(vf)
        + 0.30 * score_sa(sa)
        + 0.15 * score_pld(pld)
        + 0.20 * score_lcd(lcd)
    )


def passes_screening(
    vf: float,
    sa: float,
    pld: float,
    lcd: float,
) -> bool:
    return (
        vf >= 0.50
        and sa >= 1000.0
        and pld >= 3.0
        and lcd >= 6.0
    )


def build_cif_index() -> dict[str, Path]:
    """Index CIF files by MOFX-DB numeric ID."""

    index: dict[str, Path] = {}

    for path in CIF_DIR.glob("*.cif"):
        stem = path.stem

        # Expected format: 0015338_hMOF-6
        if "_" not in stem:
            continue

        mof_id = stem.split("_", 1)[0]

        if mof_id.isdigit():
            index[mof_id.lstrip("0") or "0"] = path

    return index


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    print("=" * 80)
    print(" HydroMatAI — SCREENING MOFX-DB 50 000 STRUCTURES")
    print("=" * 80)

    if not METADATA.exists():
        raise SystemExit(f"Metadata introuvable : {METADATA}")

    if not CIF_DIR.exists():
        raise SystemExit(f"Dossier CIF introuvable : {CIF_DIR}")

    print()
    print("===== INDEXATION CIF =====")

    cif_index = build_cif_index()

    print(f"CIF indexés : {len(cif_index):,}")

    rows: list[dict] = []
    missing_cif = 0
    screened = 0

    with METADATA.open(
        "r",
        encoding="utf-8-sig",
        errors="ignore",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            name = (row.get("name") or "").strip()
            mof_id = (row.get("id") or "").strip()

            if not name or not mof_id:
                continue

            cif_path = cif_index.get(mof_id.lstrip("0") or "0")

            if cif_path is None:
                missing_cif += 1
                continue

            vf = number(row.get("void_fraction"))
            sa = number(row.get("surface_area_m2g"))
            pld = number(row.get("pld"))
            lcd = number(row.get("lcd"))

            global_score = score_global(
                vf,
                sa,
                pld,
                lcd,
            )

            passed = passes_screening(
                vf,
                sa,
                pld,
                lcd,
            )

            if passed:
                screened += 1

            rows.append(
                {
                    "id": mof_id,
                    "name": name,
                    "cif_path": str(cif_path),
                    "void_fraction": vf,
                    "surface_area_m2g": sa,
                    "pld": pld,
                    "lcd": lcd,
                    "global_score": round(global_score, 6),
                    "screening_pass": passed,
                }
            )

    rows.sort(
        key=lambda r: (
            r["screening_pass"],
            r["global_score"],
            r["void_fraction"],
            r["surface_area_m2g"],
        ),
        reverse=True,
    )

    top100 = rows[:100]
    top20 = rows[:20]

    dft_rows = []

    for rank, row in enumerate(top20, start=1):
        dft_rows.append(
            {
                "rank": rank,
                "material": row["name"],
                "mof_id": row["id"],
                "priority": row["global_score"],
                "global": row["global_score"],
                "density": row["surface_area_m2g"],
                "ambient": 0.0,
                "cif_path": row["cif_path"],
            }
        )

    write_csv(TOP100, top100)
    write_csv(TOP20, top20)
    write_csv(DFT_PRIORITY, dft_rows)

    print()
    print("===== RÉSULTATS =====")
    print(f"Structures metadata       : {len(rows):,}")
    print(f"CIF correspondants        : {len(rows):,}")
    print(f"CIF manquants             : {missing_cif:,}")
    print(f"Structures passant filtre : {screened:,}")

    print()
    print("===== TOP 20 =====")
    print(
        f"{'RANG':<5} "
        f"{'MATERIAL':<24} "
        f"{'SCORE':>8} "
        f"{'VF':>8} "
        f"{'SA':>10} "
        f"{'PLD':>8} "
        f"{'LCD':>8}"
    )
    print("-" * 80)

    for rank, row in enumerate(top20, start=1):
        print(
            f"{rank:<5} "
            f"{row['name']:<24} "
            f"{row['global_score']:>8.4f} "
            f"{row['void_fraction']:>8.4f} "
            f"{row['surface_area_m2g']:>10.1f} "
            f"{row['pld']:>8.2f} "
            f"{row['lcd']:>8.2f}"
        )

    print()
    print("===== FICHIERS =====")
    print(f"TOP100       : {TOP100}")
    print(f"TOP20        : {TOP20}")
    print(f"DFT PRIORITY : {DFT_PRIORITY}")

    print()
    print("=" * 80)
    print(" SCREENING TERMINÉ")
    print(" QE : NON LANCÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
