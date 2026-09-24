#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

print("=" * 78)
print("M2TiH6.31C — EXTRACTION CIBLEE DES DONNEES PUBLIEES")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun CIF modifié")
print()

# Recherche UNIQUEMENT dans les zones pertinentes
roots = [
    BASE / "reports",
    BASE / "calculations",
    BASE / "literature",
    BASE / "data",
    BASE / "docs",
]

keywords = [
    "Ba2TiH6",
    "Sr2TiH6",
    "M2TiH6",
    "Karafi",
    "113778",
    "5847695",
]

allowed_ext = {
    ".txt", ".csv", ".md", ".html", ".htm",
    ".cif", ".json", ".yaml", ".yml"
}

print("===== 1. RECHERCHE CIBLEE =====")
print()

files = []

for root in roots:
    if not root.exists():
        continue

    for p in root.rglob("*"):
        if not p.is_file():
            continue

        if p.suffix.lower() not in allowed_ext:
            continue

        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue

        low = text.lower()

        if any(k.lower() in low for k in keywords):
            files.append(p)

files = sorted(set(files))

if not files:
    print("[INFO] Aucun document cible trouvé.")
else:
    for p in files:
        print(f"[FOUND] {p}")

print()

print("===== 2. RECHERCHE DES VALEURS STRUCTURALES =====")
print()

# Expressions volontairement assez larges.
patterns = [
    r"\ba\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*(?:Å|A|angstrom)?",
    r"\ba\s*\(\s*Å\s*\)\s*=\s*([0-9]+(?:\.[0-9]+)?)",
    r"lattice\s+parameter\s*(?:a)?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
    r"lattice\s+constant\s*(?:a)?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
    r"cell\s+parameter\s*(?:a)?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
]

hits = []

for p in files:
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue

    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            value = float(m.group(1))

            # Domaine raisonnable pour une maille cubique M2TiH6
            if 3.0 <= value <= 10.0:
                start = max(0, m.start() - 180)
                end = min(len(text), m.end() + 180)

                context = " ".join(
                    text[start:end].split()
                )

                hits.append((p, value, context))

if hits:
    for p, value, context in hits:
        print(f"[CANDIDATE] {p}")
        print(f"  a = {value:.8f} A")
        print(f"  contexte = {context}")
        print()
else:
    print("[INFO] Aucune valeur structurale candidate trouvée.")

print()

print("===== 3. RECHERCHE DES POSITIONS / WYCKOFF =====")
print()

position_patterns = [
    r"Ba.*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+)",
    r"Sr.*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+)",
    r"Ti.*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+)",
    r"H.*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+).*?([0-9]+\.[0-9]+)",
]

for p in files:
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue

    if not any(x in text for x in ["Ba2TiH6", "Sr2TiH6"]):
        continue

    for line in text.splitlines():
        low = line.lower()

        if any(x in low for x in ["ba", "sr", "ti", " h ", "hydrogen"]):
            if any(c in line for c in ["0.", "1.0", "1.00"]):
                print(f"[POSITION?] {p}")
                print(f"  {line[:300]}")

print()

print("===== 4. PREPRINT =====")
print()
print("DOI préprint : 10.2139/ssrn.5847695")
print("Titre : Exploring M2TiH6 (M = Ba, Sr) Hydride Perovskites")
print()

print("===== 5. ETAT =====")
print()

if hits:
    print("[IMPORTANT] Valeur(s) candidate(s) trouvée(s).")
    print("[ACTION] Ne pas les utiliser directement : validation requise.")
else:
    print("[BLOCK] Aucune valeur numérique locale fiable.")
    print("[ACTION] Le Tableau 1/PDF doit être fourni ou récupéré.")

print()
print("[SAFETY] Aucun pw.x.")
print("[SAFETY] Aucun fichier scientifique modifié.")
print("[SAFETY] Les CIF 1.000000 A restent bloqués.")

print()
print("=" * 78)
print("M2TiH6.31C — FIN")
print("=" * 78)
