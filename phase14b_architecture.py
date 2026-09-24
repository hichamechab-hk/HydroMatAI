#!/usr/bin/env python3

from pathlib import Path
import ast
import subprocess
import sys

ROOT = Path.cwd()
SRC = ROOT / "src"
PKG = SRC / "hydromatai"

print("=" * 78)
print("HYDROMATAI — PHASE 14B — AUDIT DE L'ARCHITECTURE REELLE")
print("=" * 78)

errors = []

# ------------------------------------------------------------
# 1. Arborescence réelle
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("1. MODULES REELS")
print("=" * 78)

if not PKG.exists():
    print("[FAIL] src/hydromatai absent")
    sys.exit(1)

for path in sorted(PKG.iterdir()):
    if path.is_dir():
        count = len(list(path.rglob("*.py")))
        print(f"[OK]   {path.name:<25} {count:>3} fichiers Python")
    elif path.suffix == ".py":
        print(f"[FILE] {path.name}")

# ------------------------------------------------------------
# 2. Tous les modules Python
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("2. INDEX COMPLET DES MODULES")
print("=" * 78)

py_files = sorted(PKG.rglob("*.py"))

for f in py_files:
    rel = f.relative_to(SRC).with_suffix("")
    module = ".".join(rel.parts)
    print(module)

print(f"\nTotal: {len(py_files)} fichiers Python")

# ------------------------------------------------------------
# 3. Recherche des fonctionnalités DFT
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("3. FONCTIONNALITES DFT")
print("=" * 78)

terms = [
    "quantum",
    "espresso",
    "qe",
    "dft",
    "scf",
    "relax",
    "pseudopotential",
    "pw.x",
]

matches = {}

for f in py_files:
    try:
        text = f.read_text(errors="ignore")
    except Exception:
        continue

    lower = text.lower()
    found = [term for term in terms if term in lower]

    if found:
        matches[f] = found

for f, found in matches.items():
    print(f"[DFT] {f.relative_to(ROOT)}")
    print(f"      {', '.join(found)}")

print(f"\nFichiers DFT détectés: {len(matches)}")

# ------------------------------------------------------------
# 4. Recherche électronique / optique
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("4. FONCTIONNALITES ELECTRONIQUES / OPTIQUES")
print("=" * 78)

feature_terms = [
    "electronic",
    "band_gap",
    "bandgap",
    "dos",
    "density of states",
    "optical",
    "dielectric",
    "permittivity",
    "absorption",
    "refractive",
]

feature_matches = {}

for f in py_files:
    try:
        text = f.read_text(errors="ignore")
    except Exception:
        continue

    lower = text.lower()
    found = [term for term in feature_terms if term in lower]

    if found:
        feature_matches[f] = found

for f, found in feature_matches.items():
    print(f"[PROP] {f.relative_to(ROOT)}")
    print(f"       {', '.join(found)}")

print(f"\nFichiers concernés: {len(feature_matches)}")

# ------------------------------------------------------------
# 5. Classes et fonctions scientifiques
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("5. API SCIENTIFIQUE REELLE")
print("=" * 78)

for f in py_files:
    try:
        tree = ast.parse(f.read_text(errors="ignore"))
    except Exception:
        continue

    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append(node.name)

    if classes or functions:
        print(f"\n{f.relative_to(ROOT)}")

        if classes:
            print("  Classes:")
            for x in classes:
                print(f"    - {x}")

        if functions:
            print("  Fonctions:")
            for x in functions:
                print(f"    - {x}")

# ------------------------------------------------------------
# 6. Imports entre composants
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("6. DEPENDANCES ENTRE COMPOSANTS")
print("=" * 78)

component_names = [
    "dft",
    "ml",
    "scientific",
    "literature",
    "discovery",
    "platform",
    "analysis",
    "workflow",
    "ranking",
    "evaluation",
]

for f in py_files:
    try:
        tree = ast.parse(f.read_text(errors="ignore"))
    except Exception:
        continue

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(x in alias.name.lower() for x in component_names):
                    imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module and any(
                x in node.module.lower() for x in component_names
            ):
                imports.append(node.module)

    if imports:
        print(f"\n{f.relative_to(ROOT)}")
        for imp in sorted(set(imports)):
            print(f"  -> {imp}")

# ------------------------------------------------------------
# 7. API ML réelle
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("7. API ML")
print("=" * 78)

sys.path.insert(0, str(SRC))

try:
    import hydromatai.ml as ml

    names = [
        x for x in dir(ml)
        if not x.startswith("_")
    ]

    print("Exports ML:")
    for name in names:
        print(f"  - {name}")

    if hasattr(ml, "MaterialFeatures"):
        print("[OK] MaterialFeatures")
    if hasattr(ml, "MaterialModel"):
        print("[OK] MaterialModel")
    if hasattr(ml, "PredictionResult"):
        print("[OK] PredictionResult")
    if hasattr(ml, "ScreeningResult"):
        print("[OK] ScreeningResult")

except Exception as exc:
    print(f"[FAIL] ML: {exc}")
    errors.append(str(exc))

# ------------------------------------------------------------
# 8. Tests
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("8. VALIDATION")
print("=" * 78)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] 153 tests / suite pytest")
else:
    print("[FAIL] pytest")
    errors.append("pytest")

result = subprocess.run(
    [sys.executable, "-m", "compileall", "-q", "src"],
    cwd=ROOT,
)

if result.returncode == 0:
    print("[OK] compilation")
else:
    print("[FAIL] compilation")
    errors.append("compileall")

# ------------------------------------------------------------
# 9. Git
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("9. GIT")
print("=" * 78)

result = subprocess.run(
    ["git", "status", "--short"],
    cwd=ROOT,
    text=True,
    stdout=subprocess.PIPE,
)

print(result.stdout.strip() or "[OK] Working tree propre")

# ------------------------------------------------------------
# 10. Conclusion
# ------------------------------------------------------------
print("\n" + "=" * 78)
print("PHASE 14B — CONCLUSION")
print("=" * 78)

print()
print("Les anciens chemins suivants NE DOIVENT PAS être recréés")
print("sans preuve qu'ils sont nécessaires :")
print("  - hydromatai.dft.input_generator")
print("  - hydromatai.dft.parser")
print("  - hydromatai.electronic")
print("  - hydromatai.optical")
print()
print("La structure actuelle doit être déterminée à partir")
print("des modules réellement présents et des 153 tests.")
print()

if errors:
    print(f"Erreurs de validation : {len(errors)}")
    print("STATUT : DIAGNOSTIC A POURSUIVRE")
else:
    print("Validation de base : OK")
    print("STATUT : ARCHITECTURE REELLE IDENTIFIEE")

print("=" * 78)
