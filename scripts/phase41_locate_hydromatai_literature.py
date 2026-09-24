from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")

print("=" * 70)
print("PHASE 41 — LOCALISATION DU MODULE HYDROMATAI.LITERATURE")
print("-" * 70)

files = []

for p in ROOT.rglob("*.py"):
    if not p.is_file():
        continue
    if any(part in {".venv", "__pycache__", ".git"} for part in p.parts):
        continue

    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if (
        "def import_literature_csv" in text
        or "def build_ambient_benchmark" in text
        or "class ScientificWorkflow" in text
        or "hydromatai.literature" in text
    ):
        files.append(p.resolve())

print(f"FICHIERS CANDIDATS : {len(files)}")
print()

for p in sorted(files):
    print(p)

print()
print("-" * 70)
print("DEFINITIONS EXACTES")
print("-" * 70)

found = False

for p in sorted(files):
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        continue

    for i, line in enumerate(lines, 1):
        s = line.strip()

        if (
            s.startswith("def import_literature_csv")
            or s.startswith("def build_ambient_benchmark")
            or s.startswith("class ScientificWorkflow")
        ):
            print(f"{p}:L{i}: {s}")
            found = True

print()
print("=" * 70)

if found:
    print("STATUS : DEFINITIONS_FOUND")
else:
    print("STATUS : DEFINITIONS_NOT_FOUND")

print("=" * 70)
