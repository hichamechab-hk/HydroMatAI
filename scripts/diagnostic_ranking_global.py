from __future__ import annotations
import os
os.system("clear")

import csv
import statistics
from pathlib import Path


CSV_PATH = Path("reports/global_screening/global_audit.csv")


def to_float(value: str | None) -> float | None:
    try:
        if value in (None, "", "None"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values))

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return (
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )


def describe(
    name: str,
    values: list[float],
) -> None:
    print()
    print(name)
    print("-" * 80)

    if not values:
        print("Aucune donnée")
        return

    print(f"  n       : {len(values):,}")
    print(f"  min     : {min(values):.6f}")
    print(f"  P25     : {percentile(values, 0.25):.6f}")
    print(f"  médiane : {percentile(values, 0.50):.6f}")
    print(f"  P75     : {percentile(values, 0.75):.6f}")
    print(f"  P90     : {percentile(values, 0.90):.6f}")
    print(f"  P95     : {percentile(values, 0.95):.6f}")
    print(f"  P99     : {percentile(values, 0.99):.6f}")
    print(f"  max     : {max(values):.6f}")
    print(f"  moyenne : {statistics.fmean(values):.6f}")


def main() -> None:
    print("=" * 80)
    print(" HydroMatAI — DIAGNOSTIC RANKING GLOBAL")
    print("=" * 80)

    if not CSV_PATH.exists():
        print()
        print("ERREUR : fichier introuvable")
        print(f"  {CSV_PATH}")
        return

    print()
    print(f"Fichier : {CSV_PATH}")

    total = 0
    valid = 0
    duplicates = 0
    candidates = 0

    mofxdb_total = 0
    mofxdb_candidates = 0

    scores = []
    mof_scores = []

    void_fraction = []
    surface_area = []
    pld = []
    lcd = []

    score_1_count = 0
    score_ge_099 = 0
    score_ge_095 = 0
    score_ge_090 = 0
    score_lt_050 = 0

    with CSV_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            total += 1

            if row.get("valid") == "1":
                valid += 1

            if row.get("duplicate") == "1":
                duplicates += 1

            if (
                row.get("passes_screening") == "1"
                and row.get("duplicate") != "1"
            ):
                candidates += 1

            source = row.get("source", "")

            score = to_float(row.get("score"))

            if score is not None:
                scores.append(score)

                if score >= 1.0:
                    score_1_count += 1

                if score >= 0.99:
                    score_ge_099 += 1

                if score >= 0.95:
                    score_ge_095 += 1

                if score >= 0.90:
                    score_ge_090 += 1

                if score < 0.50:
                    score_lt_050 += 1

            if source == "MOFXDB":
                mofxdb_total += 1

                if row.get("passes_screening") == "1":
                    mofxdb_candidates += 1

                if score is not None:
                    mof_scores.append(score)

                value = to_float(
                    row.get("void_fraction")
                )
                if value is not None:
                    void_fraction.append(value)

                value = to_float(
                    row.get("surface_area_m2g")
                )
                if value is not None:
                    surface_area.append(value)

                value = to_float(row.get("pld"))
                if value is not None:
                    pld.append(value)

                value = to_float(row.get("lcd"))
                if value is not None:
                    lcd.append(value)

    print()
    print("=" * 80)
    print(" RÉSUMÉ")
    print("=" * 80)

    print(f"Total lignes       : {total:,}")
    print(f"Valides            : {valid:,}")
    print(f"Doublons           : {duplicates:,}")
    print(f"Candidats uniques  : {candidates:,}")

    print()
    print("MOFXDB")
    print("-" * 80)
    print(f"Total              : {mofxdb_total:,}")
    print(f"Candidats          : {mofxdb_candidates:,}")

    print()
    print("=" * 80)
    print(" SATURATION DU SCORE")
    print("=" * 80)

    print(f"Score = 1.000000    : {score_1_count:,}")
    print(f"Score >= 0.99       : {score_ge_099:,}")
    print(f"Score >= 0.95       : {score_ge_095:,}")
    print(f"Score >= 0.90       : {score_ge_090:,}")
    print(f"Score < 0.50        : {score_lt_050:,}")

    if mof_scores:
        percentage = (
            100.0 * score_1_count / len(mof_scores)
        )

        print()
        print(
            f"Proportion score=1  : "
            f"{percentage:.2f}% "
            f"(toutes sources)"
        )

    describe(
        "SCORE GLOBAL",
        scores,
    )

    describe(
        "SCORE MOFXDB",
        mof_scores,
    )

    print()
    print("=" * 80)
    print(" DISTRIBUTIONS MOFXDB")
    print("=" * 80)

    describe(
        "VOID FRACTION",
        void_fraction,
    )

    describe(
        "SURFACE AREA (m²/g)",
        surface_area,
    )

    describe(
        "PLD (Å)",
        pld,
    )

    describe(
        "LCD (Å)",
        lcd,
    )

    print()
    print("=" * 80)
    print(" CONCLUSION AUTOMATIQUE")
    print("=" * 80)

    if mof_scores:
        mof_score_1 = sum(
            1
            for value in mof_scores
            if value >= 1.0
        )

        ratio = mof_score_1 / len(mof_scores)

        if ratio >= 0.50:
            print(
                "⚠️ FORTE SATURATION : "
                f"{ratio * 100:.2f}% des MOFXDB "
                "ont un score >= 1.0."
            )
            print(
                "Le score actuel est trop peu discriminant "
                "pour le classement final."
            )

        elif ratio >= 0.20:
            print(
                "⚠️ SATURATION MODÉRÉE : "
                f"{ratio * 100:.2f}% des MOFXDB "
                "ont un score >= 1.0."
            )
            print(
                "Une amélioration du ranking est recommandée."
            )

        else:
            print(
                "✅ Le score conserve une bonne "
                "capacité de discrimination."
            )

    print()
    print("=" * 80)
    print(" FIN DU DIAGNOSTIC")
    print("=" * 80)


if __name__ == "__main__":
    main()
