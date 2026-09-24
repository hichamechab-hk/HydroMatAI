#!/usr/bin/env python3

from pathlib import Path

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

TARGETS = [
    "Fe.pbe-spn-rrkjus_psl.0.2.1.UPF",
    "H.pbe-kjpaw.UPF",
    "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
]

SEARCH_ROOTS = [
    BASE / "calculations",
    BASE / "results",
    BASE / "pseudo",
    BASE / "pseudos",
    BASE / "data",
    BASE / "src",
    BASE / "external",
    BASE / "HydroMatAI_MOF",
    Path("/home/hk/HydroMatAI_MOF"),
    Path("/home/hk/software/qe-7.5"),
]

print("=" * 100)
print("PHASE 79.12A — LOCALISATION PSEUDOPOTENTIELS TiFeH2")
print("=" * 100)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun fichier copié")
print("[INFO] Aucun fichier modifié")
print("[INFO] Aucun calcul QE")

found = {}

for target in TARGETS:
    print("\n" + "-" * 100)
    print(f"[TARGET] {target}")
    print("-" * 100)

    matches = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        try:
            for p in root.rglob(target):
                if p.is_file():
                    rp = p.resolve()

                    if rp not in matches:
                        matches.append(rp)

        except (PermissionError, OSError):
            continue

    found[target] = matches

    if not matches:
        print("[FAIL] Aucun fichier trouvé")
    else:
        print(f"[PASS] {len(matches)} occurrence(s)")

        for i, p in enumerate(matches, 1):
            try:
                size = p.stat().st_size
            except OSError:
                size = -1

            print(f"[{i:02d}] {p}")
            print(f"     taille = {size} octets")

# ======================================================================
# VERIFICATION GROUPE
# ======================================================================

print("\n" + "=" * 100)
print("RÉSULTAT")
print("=" * 100)

all_found = True

for target in TARGETS:
    if found[target]:
        print(f"[PASS] {target}")
    else:
        print(f"[FAIL] {target}")
        all_found = False

if all_found:
    print("\n[RESULT] PASS — les 3 pseudopotentiels sont localisés.")
    print("[INFO] Aucune copie n'a été effectuée.")
    print("[INFO] La prochaine phase pourra utiliser leur répertoire réel.")
else:
    print("\n[RESULT] FAIL — au moins un pseudopotentiel est introuvable.")
    print("[INFO] Aucun fichier n'a été modifié.")
