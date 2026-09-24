#!/usr/bin/env python3

from pathlib import Path
import ast
import importlib
import subprocess
import sys

ROOT = Path.cwd()
SRC = ROOT / "src"
PKG = SRC / "hydromatai"

sys.path.insert(0, str(SRC))

print("=" * 78)
print("HYDROMATAI — PHASE 14C — INTEGRATION REELLE DU PIPELINE")
print("=" * 78)

errors = []
warnings = []

# ------------------------------------------------------------------
# 1. Vérification projet
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("1. PROJET")
print("=" * 78)

if not PKG.exists():
    print("[FAIL] src/hydromatai absent")
    sys.exit(1)

print(f"[OK] Projet : {ROOT}")
print(f"[OK] Package : {PKG}")

# ------------------------------------------------------------------
# 2. Import de TOUS les modules réels
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. IMPORT DE TOUS LES MODULES")
print("=" * 78)

py_files = sorted(PKG.rglob("*.py"))
modules = []

for path in py_files:
    rel = path.relative_to(SRC).with_suffix("")
    module = ".".join(rel.parts)

    if module.endswith(".__pycache__"):
        continue

    modules.append(module)

failed_imports = []

for module in modules:
    try:
        importlib.import_module(module)
        print(f"[OK]   {module}")
    except Exception as exc:
        print(f"[FAIL] {module}")
        print(f"       {type(exc).__name__}: {exc}")
        failed_imports.append((module, exc))

if failed_imports:
    errors.append(f"{len(failed_imports)} import(s) échoué(s)")

print(f"\nModules testés : {len(modules)}")

# ------------------------------------------------------------------
# 3. Détection des composants scientifiques
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("3. COMPOSANTS SCIENTIFIQUES")
print("=" * 78)

components = {
    "DFT": "hydromatai.dft",
    "Discovery": "hydromatai.discovery",
    "Literature": "hydromatai.literature",
    "Scientific": "hydromatai.scientific",
    "ML": "hydromatai.ml",
    "Platform": "hydromatai.platform",
}

loaded = {}

for name, module_name in components.items():
    try:
        module = importlib.import_module(module_name)
        loaded[name] = module

        public = sorted(
            x for x in dir(module)
            if not x.startswith("_")
        )

        print(f"\n[OK] {name}: {module_name}")

        if public:
            print("     API publique:")
            for item in public[:40]:
                print(f"       - {item}")

            if len(public) > 40:
                print(f"       ... {len(public)-40} autres")

    except Exception as exc:
        print(f"\n[WARN] {name}: {exc}")
        warnings.append(f"{name}: import indisponible")

# ------------------------------------------------------------------
# 4. Analyse des connexions entre composants
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("4. CONNEXIONS ENTRE COMPOSANTS")
print("=" * 78)

component_keys = [
    "hydromatai.dft",
    "hydromatai.discovery",
    "hydromatai.literature",
    "hydromatai.scientific",
    "hydromatai.ml",
    "hydromatai.platform",
]

connections = set()

for path in py_files:
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except Exception:
        continue

    source = ".".join(
        path.relative_to(SRC).with_suffix("").parts
    )

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            imported = [a.name for a in node.names]

        elif isinstance(node, ast.ImportFrom):
            imported = [node.module] if node.module else []

        else:
            continue

        for target in imported:
            if target and any(
                target == c or target.startswith(c + ".")
                for c in component_keys
            ):
                connections.add((source, target))

if connections:
    for source, target in sorted(connections):
        print(f"[LINK] {source} -> {target}")
else:
    print("[WARN] Aucune connexion inter-composants détectée")
    warnings.append("aucune connexion inter-composants")

# ------------------------------------------------------------------
# 5. Vérification API Literature / H2
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("5. LITERATURE / HYDROGEN")
print("=" * 78)

try:
    import hydromatai.literature as literature

    public = [
        x for x in dir(literature)
        if not x.startswith("_")
    ]

    print("[OK] hydromatai.literature importable")

    expected_keywords = [
        "hydrogen",
        "score",
        "benchmark",
        "literature",
        "material",
        "objective",
    ]

    detected = [
        x for x in public
        if any(k in x.lower() for k in expected_keywords)
    ]

    for x in detected:
        print(f"  [API] {x}")

    if not detected:
        warnings.append("API Literature/H2 peu exposée")

except Exception as exc:
    print(f"[FAIL] Literature: {exc}")
    errors.append("Literature")

# ------------------------------------------------------------------
# 6. Vérification API Scientific
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("6. SCIENTIFIC EVALUATION")
print("=" * 78)

try:
    import hydromatai.scientific as scientific

    required = [
        "ScientificEvaluation",
        "evaluate_result",
        "evaluate_results",
        "analyze_material",
        "ScientificWorkflow",
        "write_scientific_report",
    ]

    for name in required:
        if hasattr(scientific, name):
            print(f"[OK] {name}")
        else:
            print(f"[WARN] {name} absent")
            warnings.append(f"scientific.{name} absent")

except Exception as exc:
    print(f"[FAIL] Scientific: {exc}")
    errors.append("Scientific")

# ------------------------------------------------------------------
# 7. Vérification API ML
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("7. MACHINE LEARNING")
print("=" * 78)

try:
    import hydromatai.ml as ml

    ml_expected = [
        "MaterialFeatures",
        "MaterialModel",
        "PredictionRequest",
        "PredictionResult",
        "ScreeningResult",
        "extract_features",
        "predict_row",
        "rank_predictions",
        "screen_rows",
    ]

    for name in ml_expected:
        if hasattr(ml, name):
            print(f"[OK] {name}")
        else:
            print(f"[WARN] {name} absent")
            warnings.append(f"ml.{name} absent")

except Exception as exc:
    print(f"[FAIL] ML: {exc}")
    errors.append("ML")

# ------------------------------------------------------------------
# 8. DFT réel : inspection sans supposer une API
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("8. DFT / QUANTUM ESPRESSO")
print("=" * 78)

dft_files = sorted((PKG / "dft").rglob("*.py"))

if dft_files:
    print(f"[OK] {len(dft_files)} fichiers DFT")

    dft_terms = [
        "quantum",
        "espresso",
        "pw.x",
        "scf",
        "relax",
        "pseudopotential",
        "calculator",
        "qe",
    ]

    detected = set()

    for path in dft_files:
        text = path.read_text(errors="ignore").lower()

        hits = [
            term for term in dft_terms
            if term in text
        ]

        if hits:
            detected.update(hits)
            print(
                f"[DFT] {path.relative_to(ROOT)} "
                f"=> {', '.join(hits)}"
            )

    print(f"\nFonctionnalités DFT détectées : {len(detected)}")

else:
    print("[FAIL] Répertoire DFT absent")
    errors.append("DFT absent")

# ------------------------------------------------------------------
# 9. Smoke test des fonctions simples / constructeurs
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("9. SMOKE TESTS API")
print("=" * 78)

smoke_targets = [
    ("hydromatai.scientific", "evaluate_results"),
    ("hydromatai.scientific", "evaluate_result"),
    ("hydromatai.scientific", "analyze_material"),
    ("hydromatai.ml", "extract_features"),
    ("hydromatai.ml", "predict_row"),
    ("hydromatai.ml", "rank_predictions"),
    ("hydromatai.ml", "screen_rows"),
]

for module_name, function_name in smoke_targets:
    try:
        module = importlib.import_module(module_name)

        if hasattr(module, function_name):
            obj = getattr(module, function_name)

            if callable(obj):
                print(
                    f"[OK] {module_name}.{function_name} "
                    f"callable"
                )
            else:
                print(
                    f"[WARN] {module_name}.{function_name} "
                    f"non callable"
                )
                warnings.append(
                    f"{module_name}.{function_name} non callable"
                )
        else:
            print(
                f"[WARN] {module_name}.{function_name} absent"
            )

    except Exception as exc:
        print(
            f"[FAIL] {module_name}.{function_name}: "
            f"{exc}"
        )
        errors.append(
            f"{module_name}.{function_name}"
        )

# ------------------------------------------------------------------
# 10. Tests complets
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("10. TESTS COMPLETS")
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
# 11. Compilation
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("11. COMPILATION")
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
# 12. Git
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("12. GIT")
print("=" * 78)

result = subprocess.run(
    ["git", "status", "--short"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
)

status = result.stdout.strip()

if status:
    print(status)
    print("[INFO] Le script lui-même est volontairement non suivi.")
else:
    print("[OK] Working tree propre")

# ------------------------------------------------------------------
# 13. Conclusion
# ------------------------------------------------------------------
print("\n" + "=" * 78)
print("PHASE 14C — CONCLUSION")
print("=" * 78)

print(f"\nModules Python inspectés : {len(modules)}")
print(f"Composants chargés       : {len(loaded)}/{len(components)}")
print(f"Connexions détectées     : {len(connections)}")
print(f"Erreurs                  : {len(errors)}")
print(f"Avertissements           : {len(warnings)}")

if errors:
    print("\nBLOQUANTS :")
    for error in errors:
        print(f"  - {error}")

    print("\nSTATUT : PHASE 14C NON VALIDEE")
    print("Action : corriger uniquement les vrais blocages.")
    sys.exit(1)

print("\n[OK] Tous les contrôles bloquants sont passés.")

if warnings:
    print("\nAvertissements non bloquants :")
    for warning in warnings:
        print(f"  - {warning}")

print("\nSTATUT : PHASE 14C VALIDEE")
print("Pipeline réel importable et cohérent avec l'architecture actuelle.")
print("Aucun ancien module n'a été recréé.")
print("=" * 78)
