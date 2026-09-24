from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations" / "new_campaign" / "TiFeH2"
REPORTS = BASE / "reports"

print("=" * 78)
print("PHASE 78.25 — DEEP ELECTRONIC REPORTS AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

# ----------------------------------------------------------------------
# 1. RAPPORTS PHASE 78.3.x
# ----------------------------------------------------------------------

print("=" * 78)
print("1. RAPPORTS PHASE 78.3.x")
print("=" * 78)

targets = [
    "PHASE_78_3_3_CBANDS_AUDIT.txt",
    "PHASE_78_3_4_CBANDS_LOCALIZATION.txt",
    "PHASE_78_3_8_CBANDS_LOCALIZATION.txt",
    "PHASE_78_3_9_DIRECT_CBANDS_AUDIT.txt",
]

found = []

for name in targets:
    path = REPORTS / name

    if not path.exists():
        print(f"[ABSENT] {name}")
        continue

    found.append(path)
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    print()
    print(f"[FOUND] {name}")
    print(f"  taille      : {path.stat().st_size} octets")
    print(f"  lignes      : {len(lines)}")

    # Cherche les indices réellement utiles
    patterns = [
        r"input",
        r"output",
        r"\.out",
        r"\.in",
        r"bands",
        r"band structure",
        r"cbands",
        r"fermi",
        r"eigen",
        r"vbm",
        r"cbm",
        r"gap",
        r"occupation",
        r"pw\.x",
    ]

    matches = []

    for i, line in enumerate(lines, 1):
        low = line.lower()

        if any(re.search(p, low) for p in patterns):
            matches.append((i, line.strip()))

    print(f"  lignes pertinentes : {len(matches)}")

    for i, line in matches[:20]:
        print(f"    {i}: {line}")

    if len(matches) > 20:
        print(f"    ... {len(matches)-20} lignes supplémentaires")


# ----------------------------------------------------------------------
# 2. EXTRACTION DES CHEMINS QE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("2. CHEMINS DE FICHIERS QE MENTIONNÉS")
print("=" * 78)

path_pattern = re.compile(
    r"(?:/home/hk/HydroMatAI/|calculations/|"
    r"[\w./-]+\.(?:in|out|dat|xml|UPF))"
)

for path in found:
    text = path.read_text(errors="replace")

    candidates = set()

    for line in text.splitlines():
        for match in path_pattern.findall(line):
            candidates.add(match.strip(" ,;:()[]"))

    print()
    print(f"--- {path.name} ---")

    if not candidates:
        print("  Aucun chemin explicite détecté")
    else:
        for candidate in sorted(candidates):
            print(f"  {candidate}")


# ----------------------------------------------------------------------
# 3. VÉRIFICATION DES CHEMINS EXISTANTS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("3. EXISTENCE DES FICHIERS MENTIONNÉS")
print("=" * 78)

all_text = "\n".join(
    p.read_text(errors="replace")
    for p in found
)

# Extraire les chemins absolus
absolute_paths = sorted(
    set(
        re.findall(
            r"/home/hk/HydroMatAI/[A-Za-z0-9_./+\-]+",
            all_text
        )
    )
)

for raw in absolute_paths:
    clean = raw.rstrip(".,;:)")

    p = Path(clean)

    if p.exists():
        print(f"[EXISTS] {clean}")
    else:
        print(f"[MISSING] {clean}")


# ----------------------------------------------------------------------
# 4. INVENTAIRE BANDES RÉELLES
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("4. INVENTAIRE STRICT DES BAND INPUTS / OUTPUTS")
print("=" * 78)

all_files = [
    p for p in BASE.rglob("*")
    if p.is_file()
    and ".save" not in p.parts
    and "tmp" not in p.parts
]

band_inputs = []
band_outputs = []

for p in all_files:
    low = str(p).lower()
    name = p.name.lower()

    if p.suffix.lower() == ".in" and (
        "band" in low
        or "bands" in low
        or "cbands" in low
    ):
        band_inputs.append(p)

    if p.suffix.lower() in {".out", ".dat"} and (
        "band" in low
        or "bands" in low
        or "cbands" in low
    ):
        band_outputs.append(p)

print()
print(f"Band inputs candidats  : {len(band_inputs)}")
for p in sorted(band_inputs):
    print(f"  {p.relative_to(ROOT)}")

print()
print(f"Band outputs candidats : {len(band_outputs)}")
for p in sorted(band_outputs):
    print(f"  {p.relative_to(ROOT)}")


# ----------------------------------------------------------------------
# 5. VÉRIFICATION DES CALCULATIONS ANCIENNES
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("5. RECHERCHE DES CALCULATIONS ÉLECTRONIQUES ANTÉRIEURES")
print("=" * 78)

calc_root = ROOT / "calculations"

keywords = (
    "bands",
    "band",
    "cbands",
    "dos",
    "projwfc",
    "dos.x",
    "bands.x",
)

historical = []

for p in calc_root.rglob("*"):
    if not p.is_file():
        continue

    if ".save" in p.parts:
        continue

    low = str(p).lower()

    if any(k in low for k in keywords):
        historical.append(p)

for p in sorted(historical)[:200]:
    print(p.relative_to(ROOT))

if len(historical) > 200:
    print(f"... {len(historical)-200} fichiers supplémentaires")


# ----------------------------------------------------------------------
# 6. DOS STRICT
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("6. DOS — PREUVE STRICTE")
print("=" * 78)

dos_files = []

for p in all_files:
    name = p.name.lower()
    low = str(p).lower()

    if p.suffix.lower() in {".dat", ".out", ".txt"}:
        if (
            "dos" in name
            or "projwfc" in name
            or "dos.x" in name
        ):
            dos_files.append(p)

print(f"Fichiers DOS candidats : {len(dos_files)}")

for p in sorted(dos_files):
    print(f"  {p.relative_to(ROOT)}")


# ----------------------------------------------------------------------
# 7. CONCLUSION
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("7. CONCLUSION PHASE 78.25")
print("=" * 78)

print()
print("SCF individuel :")
print("  Les sorties SCF convergées restent valides.")

print()
print("Stabilité numérique :")
print("  CUTOFF   = NUMERICAL_STABILITY_NOT_ESTABLISHED")
print("  KPOINTS  = NUMERICAL_STABILITY_NOT_ESTABLISHED")
print("  SMEARING = NUMERICAL_STABILITY_NOT_ESTABLISHED")

print()
print("DOS :")
print("  Les inputs DOS ne constituent pas à eux seuls une preuve")
print("  d'un calcul DOS exécuté.")

print()
print("BANDS :")
print("  Un rapport d'audit ne constitue pas à lui seul une sortie")
print("  brute de bands.x / pw.x bands.")

print()
print("STATUT SCIENTIFIQUE :")
print("  SCIENTIFIC_STATUS_NOT_ESTABLISHED")

print()
print("=" * 78)
print("PHASE 78.25 TERMINÉE — READ-ONLY")
print("=" * 78)
