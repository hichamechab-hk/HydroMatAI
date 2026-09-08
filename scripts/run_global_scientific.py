#!/usr/bin/env python3
from __future__ import annotations
import os
os.system("clear")

"""HydroMatAI — global scientific and ambient H2 ranking."""


from pathlib import Path

from hydromatai.literature import (
    build_ambient_benchmark,
    import_literature_csv,
)
from hydromatai.scientific import ScientificWorkflow


ROOT = Path(__file__).resolve().parents[1]

LITERATURE = (
    ROOT / "data/literature/published_results.csv"
)

REPORT_DIR = ROOT / "reports"

REPORT_FILE = (
    REPORT_DIR / "global_scientific_ranking.txt"
)


def main() -> None:
    print("=" * 70)
    print(" HydroMatAI — GLOBAL SCIENTIFIC / AMBIENT RANKING")
    print("=" * 70)

    if not LITERATURE.exists():
        raise FileNotFoundError(
            f"Literature file not found: {LITERATURE}"
        )

    # ------------------------------------------------------------
    # 1. Literature
    # ------------------------------------------------------------

    results = import_literature_csv(LITERATURE)

    materials = sorted(
        {
            result.material
            for result in results
        }
    )

    print(f"Publications : {len(results)}")
    print(f"Matériaux    : {len(materials)}")

    # ------------------------------------------------------------
    # 2. Ambient H2 benchmark
    # ------------------------------------------------------------

    benchmark = build_ambient_benchmark(results)

    ambient_by_material = {
        entry.material: entry
        for entry in benchmark
    }

    print()
    print("===== AMBIENT H2 BENCHMARK =====")

    for index, entry in enumerate(
        benchmark,
        start=1,
    ):
        if entry.pressure_mpa is None:
            pressure = "N/A"
        else:
            pressure = (
                f"{entry.pressure_mpa:.2f} MPa"
            )

        print(
            f"{index:2d}. "
            f"{entry.material:<20} "
            f"H2={entry.h2_uptake_wt_percent:g} wt% "
            f"T={entry.temperature_k:.1f} K "
            f"P={pressure:<10} "
            f"score={entry.screening_score:.4f} "
            f"{entry.confidence}"
        )

    # ------------------------------------------------------------
    # 3. Scientific analysis
    # ------------------------------------------------------------

    workflow = ScientificWorkflow(
        literature_path=LITERATURE,
    )

    scientific = []

    for material in materials:
        result = workflow.run(material)
        scientific.append(result)

    # ------------------------------------------------------------
    # 4. GLOBAL RANKING
    #
    # Priority:
    #   1. Ambient evidence available
    #   2. Ambient screening score
    #   3. Scientific score
    #
    # This prevents a default scientific score of 0.5000
    # from placing materials without ambient evidence above
    # experimentally benchmarked materials.
    # ------------------------------------------------------------

    scientific.sort(
        key=lambda result: (
            1
            if result.material in ambient_by_material
            else 0,
            (
                ambient_by_material[
                    result.material
                ].screening_score
                if result.material in ambient_by_material
                else 0.0
            ),
            result.final_score,
        ),
        reverse=True,
    )

    print()
    print("===== GLOBAL SCIENTIFIC / AMBIENT RANKING =====")

    for index, result in enumerate(
        scientific,
        start=1,
    ):
        ambient = ambient_by_material.get(
            result.material
        )

        if ambient is None:
            ambient_score = 0.0
            confidence = "N/A"
        else:
            ambient_score = (
                ambient.screening_score
            )
            confidence = ambient.confidence

        print(
            f"{index:2d}. "
            f"{result.material:<20} "
            f"ambient={ambient_score:.4f} "
            f"scientific={result.final_score:.4f} "
            f"confidence={confidence:<6} "
            f"literature={result.literature_count}"
        )

    # ------------------------------------------------------------
    # 5. Separate materials without ambient evidence
    # ------------------------------------------------------------

    no_ambient = [
        result
        for result in scientific
        if result.material not in ambient_by_material
    ]

    print()
    print("===== NO AMBIENT EVIDENCE =====")

    for index, result in enumerate(
        no_ambient,
        start=1,
    ):
        print(
            f"{index:2d}. "
            f"{result.material:<20} "
            f"scientific={result.final_score:.4f} "
            f"literature={result.literature_count}"
        )

    # ------------------------------------------------------------
    # 6. Scientific report
    # ------------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:

        handle.write(
            "HydroMatAI — GLOBAL SCIENTIFIC / AMBIENT RANKING\n"
        )
        handle.write("=" * 70)
        handle.write("\n\n")

        handle.write(
            f"Publications : {len(results)}\n"
        )
        handle.write(
            f"Matériaux    : {len(materials)}\n\n"
        )

        handle.write(
            "AMBIENT H2 BENCHMARK\n"
        )
        handle.write("-" * 70)
        handle.write("\n")

        for index, entry in enumerate(
            benchmark,
            start=1,
        ):
            pressure = (
                f"{entry.pressure_mpa:.4f} MPa"
                if entry.pressure_mpa is not None
                else "N/A"
            )

            handle.write(
                f"{index:2d}. "
                f"{entry.material:<20} "
                f"H2={entry.h2_uptake_wt_percent:g} wt% "
                f"T={entry.temperature_k:.1f} K "
                f"P={pressure:<10} "
                f"score={entry.screening_score:.4f} "
                f"{entry.confidence}\n"
            )

        handle.write("\n")
        handle.write(
            "GLOBAL SCIENTIFIC / AMBIENT RANKING\n"
        )
        handle.write("-" * 70)
        handle.write("\n")

        for index, result in enumerate(
            scientific,
            start=1,
        ):
            ambient = ambient_by_material.get(
                result.material
            )

            if ambient is None:
                ambient_score = 0.0
                confidence = "N/A"
            else:
                ambient_score = (
                    ambient.screening_score
                )
                confidence = ambient.confidence

            handle.write(
                f"{index:2d}. "
                f"{result.material:<20} "
                f"ambient={ambient_score:.4f} "
                f"scientific={result.final_score:.4f} "
                f"confidence={confidence:<6} "
                f"literature={result.literature_count}\n"
            )

        handle.write("\n")
        handle.write(
            "NO AMBIENT EVIDENCE\n"
        )
        handle.write("-" * 70)
        handle.write("\n")

        for index, result in enumerate(
            no_ambient,
            start=1,
        ):
            handle.write(
                f"{index:2d}. "
                f"{result.material:<20} "
                f"scientific={result.final_score:.4f} "
                f"literature={result.literature_count}\n"
            )

    print()
    print("===== REPORT =====")
    print(f"Rapport : {REPORT_FILE}")
    print()
    print(
        "OK — GLOBAL SCIENTIFIC RANKING TERMINÉ"
    )


if __name__ == "__main__":
    main()
