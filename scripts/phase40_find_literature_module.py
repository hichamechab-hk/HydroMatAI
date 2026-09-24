from pathlib import Path

ROOT = Path("/home/hk/HydroMatAI")

print("=" * 70)
print("PHASE 40 — LOCALISATION MODULE LITERATURE")
print("-" * 70)

patterns = [
    "literature.py",
    "*literature*.py",
]

found = set()

for pattern in patterns:
    for p in ROOT.rglob(pattern):
        if p.is_file():
            found.add(p.resolve())

print(f"FICHIERS TROUVÉS : {len(found)}")
print()

for p in sorted(found):
    print(p)

print()
print("-" * 70)
print("RECHERCHE DES DEFINITIONS")
print("-" * 70)

keywords = [
    "def import_literature_csv",
    "def build_ambient_benchmark",
]

hits = []

for p in sorted(found):
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        continue

    for i, line in enumerate(lines, start=1):
        if any(k in line for k in keywords):
            hits.append((p, i, line.strip()))

for p, line_no, line in hits:
    print(f"{p}:L{line_no}: {line}")

print()
print("=" * 70)

if hits:
    print("STATUS : MODULE_FOUND")
else:
    print("STATUS : DEFINITIONS_NOT_FOUND")

print("=" * 70)
