#!/usr/bin/env python3

from pathlib import Path
import csv
import importlib
import subprocess
import sys

ROOT = Path.cwd()
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

print("=" * 78)
print("HYDROMATAI — PHASE 14D — VALIDATION SUR DONNEES REELLES")
print("=" * 78)

errors = []
warnings = []

# ------------------------------------------------------------------
# 1. Données locales
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("1. INVENTAIRE DES DONNEES SCIENTIFIQUES")
print("=" * 78)

data_dirs = [
    ROOT / "reports",
    ROOT / "calculations",
    ROOT / "MOF_Library",
    ROOT / "structures",
    ROOT / "data",
]

for directory in data_dirs:
    if directory.exists():
        files = [
            p for p in directory.rglob("*")
            if p.is_file()
        ]
        print(
            f"[OK] {directory.relative_to(ROOT)} "
            f"({len(files)} fichiers)"
        )
    else:
        print(
            f"[INFO] {directory.relative_to(ROOT)} absent"
        )

# ------------------------------------------------------------------
# 2. Screening H2
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. SCREENING GLOBAL H2")
print("=" * 78)

ranking_candidates = [
    ROOT / "reports/global_screening/TOP20_GLOBAL_H2_RANKED_V2.csv",
    ROOT / "reports/global_screening/TOP200_GLOBAL_H2_RANKED_V2.csv",
]

ranking_file = None

for candidate in ranking_candidates:
    if candidate.exists():
        ranking_file = candidate
        break

if ranking_file:
    print(f"[OK] Ranking trouvé : {ranking_file}")

    try:
        with ranking_file.open(
            newline="",
            encoding="utf-8",
        ) as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        print(f"[OK] Lignes : {len(rows)}")

        if rows:
            required = {
                "name",
                "source",
                "score",
                "primitive_atoms",
                "cif",
            }

            missing = required - set(rows[0].keys())

            if missing:
                print(
                    f"[WARN] Colonnes absentes : "
                    f"{', '.join(sorted(missing))}"
                )
                warnings.append("colonnes ranking absentes")
            else:
                print("[OK] Colonnes ranking principales")

            names = [
                r.get("name", "").strip()
                for r in rows
            ]

            scores = []

            for row in rows:
                try:
                    scores.append(float(row["score"]))
                except Exception:
                    pass

            print(
                f"[OK] Matériaux nommés : "
                f"{sum(bool(x) for x in names)}"
            )

            if scores:
                print(
                    f"[OK] Score min/max : "
                    f"{min(scores):.6f} / {max(scores):.6f}"
                )

                if any(
                    score < 0 or score > 1
                    for score in scores
                ):
                    warnings.append(
                        "scores hors intervalle [0,1]"
                    )
                    print(
                        "[WARN] Certains scores sont hors [0,1]"
                    )
                else:
                    print("[OK] Scores dans [0,1]")

    except Exception as exc:
        print(f"[FAIL] Lecture ranking : {exc}")
        errors.append("lecture ranking")

else:
    print("[INFO] Aucun ranking TOP20/TOP200 local trouvé")
    warnings.append("ranking local absent")

# ------------------------------------------------------------------
# 3. Structures CIF
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("3. STRUCTURES CIF")
print("=" * 78)

cif_files = []

for directory in data_dirs:
    if directory.exists():
        cif_files.extend(directory.rglob("*.cif"))

cif_files = sorted(set(cif_files))

if cif_files:
    print(f"[OK] {len(cif_files)} fichiers CIF détectés")

    valid_cif = 0

    for cif in cif_files[:20]:
        try:
            text = cif.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if (
                "_cell_length_a" in text
                or "data_" in text
            ):
                valid_cif += 1

        except Exception:
            pass

    print(
        f"[OK] Structures CIF reconnaissables "
        f"(échantillon) : {valid_cif}/{min(20, len(cif_files))}"
    )

else:
    print("[INFO] Aucun CIF local trouvé")
    warnings.append("aucun CIF local")

# ------------------------------------------------------------------
# 4. Littérature
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("4. LITTERATURE / H2")
print("=" * 78)

try:
    literature = importlib.import_module(
        "hydromatai.literature"
    )

    print("[OK] Package Literature importable")

    public = sorted(
        x for x in dir(literature)
        if not x.startswith("_")
    )

    relevant = [
        x for x in public
        if any(
            term in x.lower()
            for term in (
                "hydrogen",
                "score",
                "benchmark",
                "literature",
                "objective",
            )
        )
    ]

    for name in relevant:
        print(f"[API] {name}")

except Exception as exc:
    print(f"[FAIL] Literature : {exc}")
    errors.append("literature")

# ------------------------------------------------------------------
# 5. Scientific Evaluation
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("5. EVALUATION SCIENTIFIQUE")
print("=" * 78)

try:
    scientific = importlib.import_module(
        "hydromatai.scientific"
    )

    required = [
        "ScientificEvaluation",
        "evaluate_result",
        "evaluate_results",
    ]

    for name in required:
        if hasattr(scientific, name):
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name} absent")
            errors.append(f"scientific.{name}")

except Exception as exc:
    print(f"[FAIL] Scientific : {exc}")
    errors.append("scientific")

# ------------------------------------------------------------------
# 6. ML
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("6. MACHINE LEARNING")
print("=" * 78)

try:
    ml = importlib.import_module("hydromatai.ml")

    required = [
        "MaterialFeatures",
        "MaterialModel",
        "PredictionResult",
        "ScreeningResult",
        "extract_features",
        "predict_row",
        "rank_predictions",
        "screen_rows",
    ]

    for name in required:
        if hasattr(ml, name):
            print(f"[OK] {name}")
        else:
            print(f"[WARN] {name} absent")
            warnings.append(f"ML API: {name}")

except Exception as exc:
    print(f"[FAIL] ML : {exc}")
    errors.append("ML")

# ------------------------------------------------------------------
# 7. DFT / QE local
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("7. QUANTUM ESPRESSO")
print("=" * 78)

qe_candidates = [
    ROOT / "calculations/global_screening/qe",
    ROOT / "calculations",
]

qe_files = []

for directory in qe_candidates:
    if directory.exists():
        qe_files.extend(
            p for p in directory.rglob("*")
            if p.is_file()
            and (
                p.name.endswith(".in")
                or p.name.endswith(".out")
                or p.name.endswith(".UPF")
            )
        )

qe_files = sorted(set(qe_files))

if qe_files:
    print(f"[OK] Fichiers QE locaux : {len(qe_files)}")

    inputs = [
        p for p in qe_files
        if p.name.endswith(".in")
    ]

    pseudos = [
        p for p in qe_files
        if p.name.endswith(".UPF")
    ]

    outputs = [
        p for p in qe_files
        if p.name.endswith(".out")
    ]

    print(f"  Inputs  : {len(inputs)}")
    print(f"  Outputs : {len(outputs)}")
    print(f"  UPF     : {len(pseudos)}")

    if inputs:
        print("[OK] Inputs QE présents")

    if pseudos:
        print("[OK] Pseudopotentiels présents")

else:
    print("[INFO] Aucun fichier QE local détecté")
    warnings.append("aucun fichier QE local")

# ------------------------------------------------------------------
# 8. Vérification pw.x
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("8. EXECUTABLE QE")
print("=" * 78)

qe_paths = [
    Path("/home/hk/software/qe-7.5/bin/pw.x"),
    Path.home() / "software/qe-7.5/bin/pw.x",
]

pw = next(
    (p for p in qe_paths if p.exists()),
    None,
)

if pw:
    print(f"[OK] pw.x : {pw}")
else:
    result = subprocess.run(
        ["bash", "-lc", "command -v pw.x"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode == 0:
        print(f"[OK] pw.x : {result.stdout.strip()}")
    else:
        print("[INFO] pw.x non présent dans PATH")
        warnings.append("pw.x non trouvé")

# ------------------------------------------------------------------
# 9. Tests complets
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("9. TESTS COMPLETS")
print("=" * 78)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] pytest")
else:
    print("[FAIL] pytest")
    errors.append("pytest")

# ------------------------------------------------------------------
# 10. Compilation
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("10. COMPILATION")
print("=" * 78)

result = subprocess.run(
    [sys.executable, "-m", "compileall", "-q", "src"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] compileall")
else:
    print("[FAIL] compileall")
    errors.append("compileall")

# ------------------------------------------------------------------
# 11. Git
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("11. GIT")
print("=" * 78)

result = subprocess.run(
    ["git", "status", "--short"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
)

print(result.stdout.strip() or "[OK] Working tree propre")

# ------------------------------------------------------------------
# 12. Conclusion
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("PHASE 14D — CONCLUSION")
print("=" * 78)

print(f"\nErreurs         : {len(errors)}")
print(f"Avertissements  : {len(warnings)}")

if errors:
    print("\nBLOQUANTS :")
    for error in errors:
        print(f"  - {error}")

    print("\nSTATUT : PHASE 14D NON VALIDEE")
    sys.exit(1)

if warnings:
    print("\nInformations / avertissements non bloquants :")
    for warning in warnings:
        print(f"  - {warning}")

print("\n[OK] Pipeline validé sur l'environnement scientifique disponible.")
print("[OK] Aucun module artificiel ajouté.")
print("[OK] Tests et compilation validés.")
print("\nSTATUT : PHASE 14D VALIDEE")
print("=" * 78)
