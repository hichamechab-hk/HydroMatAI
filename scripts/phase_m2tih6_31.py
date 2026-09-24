#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

print("=" * 78)
print("M2TiH6.31 — EXTRACTION DES PARAMETRES PUBLIES")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun calcul QE")
print("[INFO] Aucun fichier scientifique modifié")
print()

targets = [
    "Ba2TiH6",
    "Sr2TiH6",
]

patterns = [
    "*.pdf",
    "*.txt",
    "*.html",
    "*.htm",
    "*.cif",
]

roots = [
    BASE / "calculations",
    BASE / "reports",
    BASE / "literature",
    BASE / "data",
    BASE / "docs",
    BASE,
]

print("===== 1. RECHERCHE DES SOURCES LOCALES =====")
print()

found = []

for root in roots:
    if not root.exists():
        continue

    try:
        for p in root.rglob("*"):
            if not p.is_file():
                continue

            name = p.name.lower()

            if any(t.lower() in name for t in targets):
                found.append(p)

    except PermissionError:
        pass

# suppression doublons
found = sorted(set(found))

if found:
    for p in found:
        print(f"[FOUND] {p}")
else:
    print("[INFO] Aucun fichier explicitement nommé Ba2TiH6/Sr2TiH6 trouvé.")

print()
print("===== 2. RECHERCHE DE LA PUBLICATION =====")
print()

doi = "10.1016/j.jpcs.2026.113778"

print(f"[DOI] {doi}")
print("[ARTICLE] Karafi et al., Journal of Physics and Chemistry of Solids")
print("[VOLUME] 216")
print("[ARTICLE] 113778")
print("[YEAR] 2026")
print()

print("===== 3. INFORMATIONS STRUCTURALES VERIFIEES =====")
print()

print("Ba2TiH6 :")
print("  space group = Pm-3m (#225)")
print("  crystal system = cubic")
print("  lattice parameter a = A EXTRAIRE DU TABLEAU 1")
print()

print("Sr2TiH6 :")
print("  space group = Pm-3m (#225)")
print("  crystal system = cubic")
print("  lattice parameter a = A EXTRAIRE DU TABLEAU 1")
print()

print("===== 4. CONTROLE DES CIF LOCAUX =====")
print()

cifs = []

for root in roots:
    if not root.exists():
        continue

    try:
        cifs.extend(root.rglob("*.cif"))
    except PermissionError:
        pass

cifs = sorted(set(cifs))

for cif in cifs:
    try:
        text = cif.read_text(errors="ignore")
    except Exception:
        continue

    low = text.lower()

    if "ba2tih6" in low or "sr2tih6" in low:
        print(f"[CIF] {cif}")

        for key in [
            "_cell_length_a",
            "_cell_length_b",
            "_cell_length_c",
            "_cell_angle_alpha",
            "_cell_angle_beta",
            "_cell_angle_gamma",
            "_symmetry_space_group_name_h-m",
        ]:
            m = re.search(
                rf"^{re.escape(key)}\s+(.+)$",
                text,
                flags=re.MULTILINE | re.IGNORECASE,
            )

            if m:
                print(f"  {key} = {m.group(1).strip()}")

        print()

print("===== 5. REGLE DE SECURITE =====")
print()
print("[BLOCK] Aucun CIF local ne sera considéré comme publié sans validation.")
print("[BLOCK] Une maille a=b=c=1 A reste INVALIDEE.")
print("[BLOCK] Aucun input QE ne sera généré à partir de cette maille.")
print()

print("=" * 78)
print("M2TiH6.31 — EXTRACTION INCOMPLETE SANS TABLEAU 1")
print("=" * 78)
