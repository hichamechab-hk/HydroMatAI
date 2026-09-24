import os
os.system("clear")

from pathlib import Path
import re
import hashlib

ROOT = Path("/home/hk/HydroMatAI")

TARGETS = {
    "HISTORICAL_CRASH":
        ROOT / "calculations/top5_dft/TiFeH2/electronic/CRASH",

    "HISTORICAL_NSCF":
        ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_nscf.out",

    "HISTORICAL_BANDS":
        ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_bands.out",

    "HISTORICAL_DOS":
        ROOT / "calculations/top5_dft/TiFeH2/electronic/TiFeH2_dos.out",

    "RELAXED_NSCF":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_nscf.out",

    "RELAXED_BANDS":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_bands.out",

    "RELAXED_DOS":
        ROOT / "calculations/top5_dft/TiFeH2/electronic_relaxed/"
        "TiFeH2_relaxed_dos.out",
}


print("=" * 78)
print("PHASE 78.31 — HISTORICAL ELECTRONIC CRASH AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier modifié")
print()


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def lines_with_patterns(text, patterns):
    result = []

    for i, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            if re.search(pattern, line, re.I):
                result.append((i, line))
                break

    return result


PATTERNS = [
    r"error",
    r"fatal",
    r"crash",
    r"stopping",
    r"cannot open",
    r"convergence has been achieved",
    r"JOB DONE",
    r"c_bands:",
    r"Fermi energy",
    r"End of band structure calculation",
]


# ----------------------------------------------------------------------
# 1. INVENTAIRE
# ----------------------------------------------------------------------

print("1. INVENTAIRE DES FICHIERS")
print("-" * 78)

for label, path in TARGETS.items():

    print()
    print(label)
    print("PATH :", path)

    if not path.exists():
        print("  [ABSENT]")
        continue

    print("  SIZE   :", path.stat().st_size)
    print("  SHA256 :", sha256(path))


# ----------------------------------------------------------------------
# 2. CRASH
# ----------------------------------------------------------------------

crash = TARGETS["HISTORICAL_CRASH"]

print()
print("=" * 78)
print("2. ANALYSE DU CRASH HISTORIQUE")
print("=" * 78)

if not crash.exists():
    print("[INFO] Aucun fichier CRASH")
else:

    text = crash.read_text(errors="replace")
    lines = text.splitlines()

    print("Lignes :", len(lines))
    print()

    for i, line in enumerate(lines, 1):
        print(f"{i:5d}: {line}")

    print()
    print("Marqueurs détectés :")

    matches = lines_with_patterns(
        text,
        [
            r"error",
            r"fatal",
            r"crash",
            r"stopping",
            r"cannot open",
            r"convergence",
        ],
    )

    if matches:
        for i, line in matches:
            print(f"  {i:5d}: {line}")
    else:
        print("  Aucun marqueur classique détecté.")


# ----------------------------------------------------------------------
# 3. RÉSUMÉ DES SORTIES HISTORIQUES
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("3. SORTIES HISTORIQUES NON-RELAXED")
print("=" * 78)

for label in [
    "HISTORICAL_NSCF",
    "HISTORICAL_BANDS",
    "HISTORICAL_DOS",
]:

    path = TARGETS[label]

    print()
    print(label)

    if not path.exists():
        print("  [ABSENT]")
        continue

    text = path.read_text(errors="replace")

    job_done = bool(
        re.search(r"\bJOB DONE\b", text, re.I)
    )

    c_bands = len(
        re.findall(r"c_bands:", text, re.I)
    )

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        text,
        re.I,
    )

    errors = re.findall(
        r"(?:Error in routine|ERROR:|fatal error|cannot open|stopping)",
        text,
        re.I,
    )

    print("  JOB DONE      :", "YES" if job_done else "NO")
    print("  c_bands       :", c_bands)
    print("  Error markers :", len(errors))

    if fermi:
        print("  Fermi final   :", fermi[-1], "eV")
    else:
        print("  Fermi final   : non trouvé")


# ----------------------------------------------------------------------
# 4. RÉSUMÉ DE LA BRANCHE RELAXED
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("4. SORTIES ELECTRONIC_RELAXED")
print("=" * 78)

for label in [
    "RELAXED_NSCF",
    "RELAXED_BANDS",
    "RELAXED_DOS",
]:

    path = TARGETS[label]

    print()
    print(label)

    if not path.exists():
        print("  [ABSENT]")
        continue

    text = path.read_text(errors="replace")

    job_done = bool(
        re.search(r"\bJOB DONE\b", text, re.I)
    )

    c_bands = len(
        re.findall(r"c_bands:", text, re.I)
    )

    fermi = re.findall(
        r"the Fermi energy is\s+([-+0-9.EeDd]+)\s+ev",
        text,
        re.I,
    )

    errors = re.findall(
        r"(?:Error in routine|ERROR:|fatal error|cannot open|stopping)",
        text,
        re.I,
    )

    print("  JOB DONE      :", "YES" if job_done else "NO")
    print("  c_bands       :", c_bands)
    print("  Error markers :", len(errors))

    if fermi:
        print("  Fermi final   :", fermi[-1], "eV")
    else:
        print("  Fermi final   : non trouvé")


# ----------------------------------------------------------------------
# 5. COMPARAISON DES BRANCHES
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("5. COMPARAISON HISTORICAL vs RELAXED")
print("=" * 78)

print()
print("Historical:")
print("  electronic/")

print()
print("Relaxed:")
print("  electronic_relaxed/")

print()
print("Interprétation :")
print("  - HISTORICAL correspond à l'ancienne branche électronique.")
print("  - RELAXED correspond à la branche utilisant la géométrie finale")
print("    du RELAX validée en Phase 78.30B.")
print("  - Un éventuel CRASH historique ne doit pas contaminer la branche")
print("    electronic_relaxed.")
print("  - Aucun remplacement ni suppression de données n'est effectué.")


# ----------------------------------------------------------------------
# 6. SYNTHÈSE
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("6. SYNTHÈSE")
print("=" * 78)

print("[OK] Audit du fichier CRASH effectué.")
print("[OK] Sorties historiques inspectées.")
print("[OK] Sorties electronic_relaxed inspectées.")
print("[OK] Les deux branches restent séparées.")
print()
print("[INFO] Aucun calcul QE lancé.")
print("[INFO] Aucun fichier modifié.")
print("[INFO] Aucun statut AIDA modifié.")

print()
print("=" * 78)
print("PHASE 78.31 TERMINÉE — READ-ONLY")
print("=" * 78)
