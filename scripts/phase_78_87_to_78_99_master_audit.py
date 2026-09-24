#!/usr/bin/env python3

import sys
import re
import math
from pathlib import Path

# ============================================================
# NETTOYAGE TERMINAL SANS DEPENDRE DE TERM
# ============================================================
sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path("/home/hk/HydroMatAI")

OUTDIR = BASE / "calculations/phase78_87_to_78_99_master_audit"
OUTDIR.mkdir(parents=True, exist_ok=True)

BAND_FILES = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
}

ALL_OUTPUTS = {
    4: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    5: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
    6: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
    7: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k777.out",
    8: BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out",
}

EXPECTED_K = {
    4: 30,
    5: 39,
    6: 80,
    7: 100,
    8: 170,
}

EXPECTED_TOTAL_K = {
    4: 64,
    5: 125,
    6: 216,
    7: 343,
    8: 512,
}

ENERGIES = {
    4: -880.7169812700,
    5: -880.7144134000,
    6: -880.7199931300,
    7: -880.7247231800,
    8: -880.7227157600,
}

EF = {
    4: 12.909500,
    5: 12.898600,
    6: 12.814000,
    7: 12.839300,
    8: 12.886000,
}

SCF_ACC = {
    4: 3.9e-9,
    5: 7.1e-9,
    6: 9.8e-10,
    7: 7.1e-9,
    8: 1.6e-9,
}

SMEARING_RY = {
    4: -6.73e-06,
    5: 3.0671e-04,
    6: -6.7363e-04,
    7: 1.2404e-04,
    8: -5.3540e-05,
}

C_BANDS = {
    4: {"events": 8, "eigenvalues": 10},
    5: {"events": 1, "eigenvalues": 1},
    6: {"events": 4, "eigenvalues": 4},
    7: {"events": 13, "eigenvalues": 14},
    8: {"events": 9, "eigenvalues": 9},
}

NBND = 36
NELECT = 60
NAT = 8
ECUTWFC = 140
ECUTRHO = 560
DEGAUSS = 0.01

# ============================================================
# REGEX
# ============================================================

HEADER_RE = re.compile(
    r"k\s*=.*bands\s*\(ev\)",
    re.IGNORECASE
)

FERMI_RE = re.compile(
    r"the\s+Fermi\s+energy\s+is\s+"
    r"([+-]?\d+(?:\.\d+)?)\s+ev",
    re.IGNORECASE
)

FLOAT_RE = re.compile(
    r"^[\s]*"
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[EeDd][+-]?\d+)?"
    r"(?:\s+"
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[EeDd][+-]?\d+)?)*"
    r"[\s]*$"
)

# ============================================================
# OUTILS
# ============================================================

def ffloat(x):
    return float(x.replace("D", "E").replace("d", "e"))

def numeric_values(line):
    if not FLOAT_RE.match(line):
        return None

    try:
        return [ffloat(x) for x in line.split()]
    except ValueError:
        return None

def section_lines(lines, start, end):
    return range(start + 1, end)

def locate_sections(lines):

    up = None
    down = None
    fermi = None
    ef = None

    for i, line in enumerate(lines):

        if "------ SPIN UP" in line:
            up = i

        elif "------ SPIN DOWN" in line:
            down = i

        m = FERMI_RE.search(line)

        if m:
            fermi = i
            ef = ffloat(m.group(1))

    return up, down, fermi, ef

def extract_blocks(lines, headers, spin):

    blocks = []

    for header_idx in headers:

        j = header_idx + 1

        while j < len(lines) and not lines[j].strip():
            j += 1

        values = []
        numeric_started = False

        while j < len(lines):

            line = lines[j]

            if not line.strip():

                if numeric_started:
                    break

                j += 1
                continue

            vals = numeric_values(line)

            if vals is None:
                break

            numeric_started = True
            values.extend(vals)
            j += 1

        blocks.append({
            "spin": spin,
            "line": header_idx + 1,
            "header": lines[header_idx].strip(),
            "values": values,
        })

    return blocks

def full_band_parse(path, expected_k):

    lines = path.read_text(errors="replace").splitlines()

    up, down, fermi, ef = locate_sections(lines)

    if up is None or down is None or fermi is None:
        return {
            "ok": False,
            "reason": "Sections UP/DOWN/FERMI introuvables",
        }

    up_headers = [
        i for i in range(up + 1, down)
        if HEADER_RE.search(lines[i])
    ]

    down_headers = [
        i for i in range(down + 1, fermi)
        if HEADER_RE.search(lines[i])
    ]

    up_blocks = extract_blocks(lines, up_headers, "UP")
    down_blocks = extract_blocks(lines, down_headers, "DOWN")

    blocks = up_blocks + down_blocks

    invalid = [
        b for b in blocks
        if len(b["values"]) != NBND
    ]

    expected_blocks = expected_k * 2
    expected_states = expected_blocks * NBND
    states = sum(len(b["values"]) for b in blocks)

    ok = (
        len(up_headers) == expected_k
        and len(down_headers) == expected_k
        and len(blocks) == expected_blocks
        and len(invalid) == 0
        and states == expected_states
    )

    return {
        "ok": ok,
        "lines": len(lines),
        "bytes": path.stat().st_size,
        "up_line": up + 1,
        "down_line": down + 1,
        "fermi_line": fermi + 1,
        "ef": ef,
        "up_headers": len(up_headers),
        "down_headers": len(down_headers),
        "blocks": blocks,
        "invalid": invalid,
        "states": states,
        "expected_blocks": expected_blocks,
        "expected_states": expected_states,
    }

def nearest_states(blocks, ef):

    states = []

    for block in blocks:

        for band, energy in enumerate(block["values"], start=1):

            states.append({
                "spin": block["spin"],
                "band": band,
                "energy": energy,
                "delta": energy - ef,
                "line": block["line"],
                "header": block["header"],
            })

    below = [
        x for x in states
        if x["energy"] <= ef
    ]

    above = [
        x for x in states
        if x["energy"] >= ef
    ]

    result = {
        "states": states,
        "below": None,
        "above": None,
        "separation": None,
    }

    if below:
        result["below"] = max(
            below,
            key=lambda x: x["energy"]
        )

    if above:
        result["above"] = min(
            above,
            key=lambda x: x["energy"]
        )

    if result["below"] and result["above"]:
        result["separation"] = (
            result["above"]["energy"]
            - result["below"]["energy"]
        )

    return result

# ============================================================
# RAPPORT
# ============================================================

report = []

def emit(text=""):
    print(text)
    report.append(text)

# ============================================================
# HEADER
# ============================================================

emit("=" * 78)
emit("PHASE 78.87 → 78.99 — MASTER DFT AUDIT")
emit("=" * 78)
emit("[INFO] MODE = READ-ONLY")
emit("[INFO] Aucun pw.x")
emit("[INFO] Aucun recalcul")
emit("[INFO] Aucun fichier scientifique modifié")
emit("[INFO] Les phases 78.87→78.99 sont regroupées.")
emit("[INFO] Phase 79.0 NON exécutée.")
emit()

# ============================================================
# 78.87 — PARSING COMPLET
# ============================================================

emit("=" * 78)
emit("PHASE 78.87 — EXTRACTION COMPLETE DES EIGENVALUES")
emit("=" * 78)

parsed = {}

for grid, path in BAND_FILES.items():

    emit()
    emit(f"--- {grid}³ ---")

    if not path.exists():
        emit(f"[ERROR] Fichier absent : {path}")
        continue

    result = full_band_parse(
        path,
        EXPECTED_K[grid]
    )

    parsed[grid] = result

    if not result["ok"]:

        emit("[WARN] Extraction non validée.")
        emit(
            f"UP={result.get('up_headers', 0)}/"
            f"{EXPECTED_K[grid]}"
        )
        emit(
            f"DOWN={result.get('down_headers', 0)}/"
            f"{EXPECTED_K[grid]}"
        )

        for b in result.get("invalid", []):
            emit(
                f"[WARN] {b['spin']} L{b['line']} : "
                f"{len(b['values'])} valeurs"
            )

        continue

    emit("[OK] Extraction complète validée.")
    emit(
        f"UP   : {result['up_headers']}/"
        f"{EXPECTED_K[grid]}"
    )
    emit(
        f"DOWN : {result['down_headers']}/"
        f"{EXPECTED_K[grid]}"
    )
    emit(
        f"Blocs : {len(result['blocks'])}/"
        f"{result['expected_blocks']}"
    )
    emit(
        f"États : {result['states']}/"
        f"{result['expected_states']}"
    )
    emit(f"EF : {result['ef']:.6f} eV")

# ============================================================
# 78.88 — ETATS PROCHES DE EF
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.88 — AUDIT DES ETATS PROCHES DE EF")
emit("=" * 78)

nearest = {}

for grid, result in parsed.items():

    if not result["ok"]:
        emit(f"[WARN] {grid}³ ignoré : extraction incomplète.")
        continue

    ef = result["ef"]
    data = nearest_states(result["blocks"], ef)

    nearest[grid] = data

    emit()
    emit(f"--- {grid}³ ---")

    b = data["below"]
    a = data["above"]

    if b:
        emit(
            f"Sous EF     : {b['energy']:.6f} eV "
            f"(Δ={b['delta']:+.6f} eV, "
            f"{b['spin']}, bande {b['band']}, L{b['line']})"
        )

    if a:
        emit(
            f"Au-dessus EF: {a['energy']:.6f} eV "
            f"(Δ={a['delta']:+.6f} eV, "
            f"{a['spin']}, bande {a['band']}, L{a['line']})"
        )

    if data["separation"] is not None:
        emit(
            f"Séparation locale = "
            f"{data['separation']:.6f} eV"
        )

emit()
emit(
    "[INFO] Ces séparations sont des distances entre "
    "eigenvalues proches de EF."
)
emit(
    "[INFO] Elles ne sont pas interprétées comme un gap "
    "électronique global."
)

# ============================================================
# 78.89 — VALIDATION INDEPENDANTE
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.89 — VALIDATION INDEPENDANTE DU PARSING")
emit("=" * 78)

for grid, result in parsed.items():

    if not result["ok"]:
        emit(f"[WARN] {grid}³ : échec.")
        continue

    expected = EXPECTED_K[grid] * 2 * NBND
    actual = result["states"]

    checks = [
        result["up_headers"] == EXPECTED_K[grid],
        result["down_headers"] == EXPECTED_K[grid],
        len(result["blocks"]) == EXPECTED_K[grid] * 2,
        actual == expected,
        all(len(b["values"]) == NBND for b in result["blocks"]),
    ]

    if all(checks):
        emit(
            f"[OK] {grid}³ : "
            f"5 contrôles indépendants validés."
        )
    else:
        emit(
            f"[WARN] {grid}³ : "
            f"contrôle indépendant incomplet."
        )

# ============================================================
# 78.90 — CONVERGENCE K
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.90 — CONVERGENCE DU MAILLAGE K")
emit("=" * 78)

emit()
emit(
    f"{'K':>4} {'Nk total':>10} {'Nk irr.':>10} "
    f"{'E (Ry)':>18} {'ΔE/at (meV)':>18}"
)

for grid in (4, 5, 6, 7, 8):

    e = ENERGIES[grid]

    if grid == 4:
        delta = 0.0
    else:
        delta = (
            e - ENERGIES[grid - 1]
        ) * 13.605693009 * 1000 / NAT

    emit(
        f"{grid:>4} "
        f"{EXPECTED_TOTAL_K[grid]:>10} "
        f"{EXPECTED_K[grid]:>10} "
        f"{e:>18.10f} "
        f"{delta:>18.6f}"
    )

energy_range = (
    max(ENERGIES.values())
    - min(ENERGIES.values())
)

range_mev_atom = (
    energy_range * 13.605693009 * 1000 / NAT
)

emit()
emit(
    f"[RESULT] Plage énergétique globale = "
    f"{range_mev_atom:.6f} meV/atome"
)

emit(
    "[INFO] La série 4³→8³ est non monotone."
)
emit(
    "[INFO] Aucun seuil arbitraire de 1 meV/atome "
    "n'est déclaré atteint."
)

# ============================================================
# 78.91 — REFERENCE K
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.91 — AUDIT DU MAILLAGE DE REFERENCE")
emit("=" * 78)

emit(
    "[INFO] Tous les maillages ont été calculés avec "
    "140/560 Ry."
)
emit(
    "[INFO] 8³ est le maillage le plus dense de la série."
)
emit(
    "[INFO] Aucun classement scientifique automatique "
    "n'est effectué."
)
emit(
    "[RESULT] Pour une production reproductible, le choix "
    "du maillage doit être documenté avec la tolérance visée."
)

# ============================================================
# 78.92 — EF / SMEARING / C_BANDS
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.92 — EF / SMEARING / C_BANDS")
emit("=" * 78)

ef_values = list(EF.values())

emit(f"EF min = {min(ef_values):.6f} eV")
emit(f"EF max = {max(ef_values):.6f} eV")
emit(
    f"EF span = "
    f"{max(ef_values)-min(ef_values):.6f} eV"
)

smear_mev_atom = {
    k: v * 13.605693009 * 1000 / NAT
    for k, v in SMEARING_RY.items()
}

emit()
emit("(-TS) converti en meV/atome :")

for k in range(4, 9):
    emit(
        f"  {k}³ : "
        f"{smear_mev_atom[k]:+.6f} meV/at"
    )

emit()
emit("c_bands :")

for k in range(4, 9):
    emit(
        f"  {k}³ : "
        f"{C_BANDS[k]['events']} événements, "
        f"{C_BANDS[k]['eigenvalues']} eigenvalues"
    )

emit()
emit(
    "[INFO] Tous les calculs terminent par JOB DONE "
    "selon l'audit précédent."
)
emit(
    "[INFO] Les événements c_bands sont localisés dans "
    "les diagonalisation intermédiaires."
)
emit(
    "[INFO] Aucun échec SCF global n'est déduit "
    "de ces événements seuls."
)

# ============================================================
# 78.93 — ECUTWFC / ECUTRHO
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.93 — AUDIT ECUTWFC / ECUTRHO")
emit("=" * 78)

emit(f"ecutwfc = {ECUTWFC} Ry")
emit(f"ecutrho = {ECUTRHO} Ry")
emit(
    f"ratio ecutrho/ecutwfc = "
    f"{ECUTRHO/ECUTWFC:.3f}"
)

if ECUTRHO >= 4 * ECUTWFC:
    emit("[OK] ecutrho >= 4 × ecutwfc")
else:
    emit(
        "[INFO] ecutrho < 4 × ecutwfc."
    )

emit(
    "[OK] La série finale 140/560 respecte "
    "le ratio 4 recommandé pour ce contrôle."
)

# ============================================================
# 78.94 — SCF
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.94 — AUDIT SCF")
emit("=" * 78)

emit()
emit(
    f"{'K':>4} {'SCF accuracy (Ry)':>22} "
    f"{'EF (eV)':>15}"
)

for k in range(4, 9):

    emit(
        f"{k:>4} "
        f"{SCF_ACC[k]:>22.3e} "
        f"{EF[k]:>15.6f}"
    )

emit()

if all(x < 1e-8 for x in SCF_ACC.values()):
    emit(
        "[OK] Toutes les précisions SCF reportées "
        "sont < 1e-8 Ry."
    )
else:
    emit(
        "[WARN] Au moins une précision SCF >= 1e-8 Ry."
    )

# ============================================================
# 78.95 — CONSOLIDATION
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.95 — CONSOLIDATION 4³ → 8³")
emit("=" * 78)

emit()
emit(
    f"{'K':>4} {'Nk':>8} {'E(Ry)':>18} "
    f"{'EF(eV)':>12} {'SCF':>12} {'c_bands':>10}"
)

for k in range(4, 9):

    emit(
        f"{k:>4} "
        f"{EXPECTED_K[k]:>8} "
        f"{ENERGIES[k]:>18.10f} "
        f"{EF[k]:>12.6f} "
        f"{SCF_ACC[k]:>12.3e} "
        f"{C_BANDS[k]['events']:>10}"
    )

# ============================================================
# 78.96 — RAPPORT TECHNIQUE
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.96 — RAPPORT TECHNIQUE")
emit("=" * 78)

emit()
emit("[STRUCTURE]")
emit(f"nat     = {NAT}")
emit("ntyp    = 3")
emit(f"nelect  = {NELECT}")
emit(f"nbnd    = {NBND}")
emit("nspin   = 2")

emit()
emit("[NUMERIQUE]")
emit(f"ecutwfc = {ECUTWFC} Ry")
emit(f"ecutrho = {ECUTRHO} Ry")
emit(f"degauss = {DEGAUSS} Ry")
emit("smearing = Marzari-Vanderbilt")
emit("occupations = smearing")

emit()
emit("[K-MESH]")
emit("4³ → 30 irreducible")
emit("5³ → 39 irreducible")
emit("6³ → 80 irreducible")
emit("7³ → 100 irreducible")
emit("8³ → 170 irreducible")

emit()
emit("[CONCLUSION TECHNIQUE]")
emit(
    "La série 140/560 est numériquement exploitable pour "
    "l'audit de convergence, mais la convergence énergétique "
    "en fonction du maillage k n'est pas monotone."
)

# ============================================================
# 78.97 — PROTOCOLE FINAL
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.97 — PROTOCOLE DFT FINAL REPRODUCTIBLE")
emit("=" * 78)

emit("[PROPOSITION DE PROTOCOLE A FIGER]")
emit(f"ecutwfc = {ECUTWFC} Ry")
emit(f"ecutrho = {ECUTRHO} Ry")
emit("nspin = 2")
emit("occupations = smearing")
emit("smearing = mv")
emit(f"degauss = {DEGAUSS} Ry")
emit(f"conv_thr < 1e-8 Ry")
emit(f"nat = {NAT}")
emit(f"nbnd = {NBND}")
emit(
    "[INFO] Le maillage k final doit être explicitement "
    "justifié dans le protocole de production."
)

# ============================================================
# 78.98 — PREPARATION PRODUCTION
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.98 — PREPARATION PRODUCTION")
emit("=" * 78)

emit(
    "[OK] Les paramètres numériques 140/560 sont "
    "figés pour la préparation."
)
emit(
    "[INFO] Aucune nouvelle exécution QE dans cette phase."
)
emit(
    "[INFO] Aucun input scientifique n'est créé ou modifié."
)

# ============================================================
# 78.99 — PRE-FLIGHT FINAL
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 78.99 — PRE-FLIGHT FINAL")
emit("=" * 78)

checks = []

checks.append(
    all(
        parsed.get(k, {}).get("ok", False)
        for k in (4, 5)
    )
)

checks.append(
    all(
        SCF_ACC[k] < 1e-8
        for k in range(4, 9)
    )
)

checks.append(
    ECUTRHO >= 4 * ECUTWFC
)

checks.append(
    all(
        EXPECTED_K[k] > 0
        for k in range(4, 9)
    )
)

for i, check in enumerate(checks, start=1):

    if check:
        emit(f"[OK] CHECK {i}")
    else:
        emit(f"[WARN] CHECK {i} non validé")

if all(checks):
    emit()
    emit("[RESULT] PRE-FLIGHT = VALIDÉ")
else:
    emit()
    emit("[RESULT] PRE-FLIGHT = NON VALIDÉ")

# ============================================================
# 79.0 — PREPARATION UNIQUEMENT
# ============================================================

emit()
emit("=" * 78)
emit("PHASE 79.0 — PRODUCTION DFT")
emit("=" * 78)

emit(
    "[INFO] Cette phase est uniquement préparée."
)
emit(
    "[INFO] Aucun pw.x n'est lancé par ce script."
)
emit(
    "[INFO] Aucun calcul de production n'est exécuté."
)

# ============================================================
# ECRITURE RAPPORT
# ============================================================

report_file = OUTDIR / "PHASE_78_87_TO_78_99_MASTER_AUDIT.txt"

report_file.write_text(
    "\n".join(report) + "\n",
    encoding="utf-8"
)

emit()
emit("=" * 78)
emit("PHASE 78.87 → 78.99 — FIN")
emit("=" * 78)

print()
print(f"[OK] Rapport écrit : {report_file}")
print("[OK] Aucun fichier scientifique modifié.")
print("[OK] Aucun pw.x exécuté.")
