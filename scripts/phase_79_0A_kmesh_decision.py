#!/usr/bin/env python3

import sys
from pathlib import Path
import math

# ============================================================
# PHASE 79.0A — DECISION NUMERIQUE DU MAILLAGE K
# ============================================================
# MODE :
#   READ-ONLY
#   Aucun pw.x
#   Aucun recalcul
#   Aucun fichier scientifique modifié
#
# OBJECTIF :
#   Déterminer si la série 4³ → 8³ permet de justifier
#   un maillage k de production.
# ============================================================

sys.stdout.write("\033[2J\033[H")
sys.stdout.flush()

ROOT = Path("/home/hk/HydroMatAI")

OUTDIR = ROOT / "calculations" / "phase_79_0A_kmesh_decision"
OUTDIR.mkdir(parents=True, exist_ok=True)

REPORT = OUTDIR / "PHASE_79_0A_KMESH_DECISION.txt"

# ============================================================
# DONNEES AUDITEES — PHASES 78.61 / 78.63 / 78.64+
# ============================================================

DATA = {
    4: {
        "nk_total": 64,
        "nk_irr": 30,
        "energy": -880.7169812700,
        "ef": 12.909500,
        "scf": 3.9e-9,
        "smearing_ry": -6.73e-06,
        "cbands_events": 8,
        "cbands_eigs": 10,
    },
    5: {
        "nk_total": 125,
        "nk_irr": 39,
        "energy": -880.7144134000,
        "ef": 12.898600,
        "scf": 7.1e-9,
        "smearing_ry": 3.0671e-04,
        "cbands_events": 1,
        "cbands_eigs": 1,
    },
    6: {
        "nk_total": 216,
        "nk_irr": 80,
        "energy": -880.7199931300,
        "ef": 12.814000,
        "scf": 9.8e-10,
        "smearing_ry": -6.7363e-04,
        "cbands_events": 4,
        "cbands_eigs": 4,
    },
    7: {
        "nk_total": 343,
        "nk_irr": 100,
        "energy": -880.7247231800,
        "ef": 12.839300,
        "scf": 7.1e-9,
        "smearing_ry": 1.2404e-04,
        "cbands_events": 13,
        "cbands_eigs": 14,
    },
    8: {
        "nk_total": 512,
        "nk_irr": 170,
        "energy": -880.7227157600,
        "ef": 12.886000,
        "scf": 1.6e-9,
        "smearing_ry": -5.3540e-05,
        "cbands_events": 9,
        "cbands_eigs": 9,
    },
}

RY_TO_EV = 13.605693009
NAT = 8

# ============================================================
# OUTILS
# ============================================================

def ev_per_atom(delta_ry):
    return abs(delta_ry) * RY_TO_EV * 1000.0 / NAT


def meV_per_atom_signed(delta_ry):
    return delta_ry * RY_TO_EV * 1000.0 / NAT


def fmt(x, digits=6):
    return f"{x:.{digits}f}"


lines = []


def out(text=""):
    print(text)
    lines.append(text)


# ============================================================
# HEADER
# ============================================================

out("=" * 78)
out("PHASE 79.0A — DECISION NUMERIQUE DU MAILLAGE K")
out("=" * 78)
out("[INFO] MODE = READ-ONLY")
out("[INFO] Aucun pw.x")
out("[INFO] Aucun recalcul")
out("[INFO] Aucun fichier scientifique modifié")
out("[INFO] Analyse des résultats déjà calculés en Phase 78.")
out("")

# ============================================================
# 1. PARAMETRES COMMUNS
# ============================================================

out("=" * 78)
out("1. PARAMETRES COMMUNS")
out("=" * 78)

out("[INFO] ecutwfc  = 140 Ry")
out("[INFO] ecutrho  = 560 Ry")
out("[INFO] ratio    = 4.000")
out("[INFO] nat      = 8")
out("[INFO] nspin    = 2")
out("[INFO] nbnd     = 36")
out("[INFO] smearing = Marzari-Vanderbilt")
out("[INFO] degauss  = 0.01 Ry")
out("")

# ============================================================
# 2. TABLEAU BRUT
# ============================================================

out("=" * 78)
out("2. TABLEAU COMPLET 4³ → 8³")
out("=" * 78)

out(
    f"{'K':>3} {'Nk':>6} {'Nk_irr':>7} "
    f"{'E(Ry)':>18} {'EF(eV)':>10} {'SCF(Ry)':>12}"
)

for k, d in DATA.items():
    out(
        f"{k:>3} "
        f"{d['nk_total']:>6} "
        f"{d['nk_irr']:>7} "
        f"{d['energy']:>18.10f} "
        f"{d['ef']:>10.6f} "
        f"{d['scf']:>12.3e}"
    )

out("")

# ============================================================
# 3. CONVERGENCE ENERGETIQUE SUCCESSIVE
# ============================================================

out("=" * 78)
out("3. VARIATION ENERGETIQUE SUCCESSIVE")
out("=" * 78)

out(f"{'Transition':>12} {'ΔE/cell (Ry)':>18} {'ΔE/at (meV)':>18}")

successive = []

for a, b in zip(range(4, 8), range(5, 9)):
    delta = DATA[b]["energy"] - DATA[a]["energy"]
    mev = meV_per_atom_signed(delta)

    successive.append((a, b, delta, mev))

    out(
        f"{a}³ → {b}³     "
        f"{delta:>18.10f} "
        f"{mev:>18.6f}"
    )

out("")

# ============================================================
# 4. PLAGE GLOBALE
# ============================================================

energies = [d["energy"] for d in DATA.values()]
emin = min(energies)
emax = max(energies)

global_range_ry = emax - emin
global_range_mev = global_range_ry * RY_TO_EV * 1000.0 / NAT

out("=" * 78)
out("4. PLAGE ENERGETIQUE GLOBALE")
out("=" * 78)

out(f"Emin = {emin:.10f} Ry")
out(f"Emax = {emax:.10f} Ry")
out(f"Plage = {global_range_ry:.10f} Ry")
out(f"Plage = {global_range_mev:.6f} meV/atome")
out("")

# ============================================================
# 5. TESTS DE TOLERANCE
# ============================================================

out("=" * 78)
out("5. TESTS DE TOLERANCE")
out("=" * 78)

tolerances = [10.0, 5.0, 2.0, 1.0]

for tol in tolerances:
    out(f"[TOLERANCE] {tol:.1f} meV/atome")

    for a, b, delta, mev in successive:
        passed = abs(mev) <= tol
        state = "PASS" if passed else "FAIL"

        out(
            f"  {a}³→{b}³ : "
            f"{abs(mev):.6f} meV/at "
            f"[{state}]"
        )

    out("")

# ============================================================
# 6. STABILITE DE EF
# ============================================================

out("=" * 78)
out("6. STABILITE DU NIVEAU DE FERMI")
out("=" * 78)

efs = [d["ef"] for d in DATA.values()]
ef_min = min(efs)
ef_max = max(efs)
ef_span = ef_max - ef_min

out(f"EF min  = {ef_min:.6f} eV")
out(f"EF max  = {ef_max:.6f} eV")
out(f"EF span = {ef_span:.6f} eV")
out("")

out("[INFO] Variations de EF :")

for a, b in zip(range(4, 8), range(5, 9)):
    delta_ef = DATA[b]["ef"] - DATA[a]["ef"]

    out(
        f"  {a}³ → {b}³ : "
        f"{delta_ef:+.6f} eV"
    )

out("")

# ============================================================
# 7. SMEARING
# ============================================================

out("=" * 78)
out("7. CONTRIBUTION (-TS)")
out("=" * 78)

out(f"{'K':>3} {'(-TS) Ry':>16} {'meV/at':>16}")

for k, d in DATA.items():
    mev = d["smearing_ry"] * RY_TO_EV * 1000.0 / NAT

    out(
        f"{k:>3} "
        f"{d['smearing_ry']:>16.8e} "
        f"{mev:>16.6f}"
    )

out("")

smearing_mev = [
    d["smearing_ry"] * RY_TO_EV * 1000.0 / NAT
    for d in DATA.values()
]

smearing_span = max(smearing_mev) - min(smearing_mev)

out(
    f"[RESULT] Plage (-TS) = "
    f"{smearing_span:.6f} meV/atome"
)
out("")

# ============================================================
# 8. SCF
# ============================================================

out("=" * 78)
out("8. CONTROLE SCF")
out("=" * 78)

scf_ok = True

for k, d in DATA.items():
    ok = d["scf"] < 1e-8

    if not ok:
        scf_ok = False

    state = "OK" if ok else "FAIL"

    out(
        f"{k}³ : "
        f"SCF = {d['scf']:.3e} Ry "
        f"[{state}]"
    )

out("")

if scf_ok:
    out("[OK] Toutes les précisions SCF sont < 1e-8 Ry.")
else:
    out("[WARN] Au moins une précision SCF dépasse 1e-8 Ry.")

# ============================================================
# 9. C_BANDS
# ============================================================

out("")
out("=" * 78)
out("9. AUDIT C_BANDS")
out("=" * 78)

for k, d in DATA.items():
    out(
        f"{k}³ : "
        f"{d['cbands_events']} événements, "
        f"{d['cbands_eigs']} eigenvalues"
    )

out("")
out(
    "[INFO] Les événements c_bands sont considérés ici comme "
    "des événements de diagonalisation intermédiaires."
)
out(
    "[INFO] Leur présence seule ne permet pas de conclure à "
    "un échec SCF global."
)

# ============================================================
# 10. TEST DE MONOTONICITE
# ============================================================

out("")
out("=" * 78)
out("10. TEST DE MONOTONICITE ENERGETIQUE")
out("=" * 78)

signs = []

for _, _, delta, _ in successive:
    if delta > 0:
        signs.append("+")
    elif delta < 0:
        signs.append("-")
    else:
        signs.append("0")

out("Signes successifs : " + " ".join(signs))

monotonic_decreasing = all(
    successive[i][2] <= 0
    for i in range(len(successive))
)

monotonic_increasing = all(
    successive[i][2] >= 0
    for i in range(len(successive))
)

if monotonic_decreasing or monotonic_increasing:
    out("[RESULT] Série monotone.")
else:
    out("[RESULT] Série NON monotone.")

# ============================================================
# 11. ANALYSE DU DERNIER PAS
# ============================================================

out("")
out("=" * 78)
out("11. ANALYSE 7³ → 8³")
out("=" * 78)

delta78 = DATA[8]["energy"] - DATA[7]["energy"]
delta78_mev = meV_per_atom_signed(delta78)

out(f"ΔE(8³−7³) = {delta78:.10f} Ry")
out(f"ΔE/atome   = {delta78_mev:+.6f} meV/atome")
out(f"ΔEF        = {DATA[8]['ef'] - DATA[7]['ef']:+.6f} eV")
out("")

if abs(delta78_mev) <= 1.0:
    out("[INFO] Le dernier pas est inférieur ou égal à 1 meV/atome.")
else:
    out(
        "[INFO] Le dernier pas reste supérieur à "
        "1 meV/atome."
    )

# ============================================================
# 12. DECISION OBJECTIVE
# ============================================================

out("")
out("=" * 78)
out("12. DECISION NUMERIQUE")
out("=" * 78)

out("[CRITERE A] Série complète monotone")
out(
    "  -> "
    + ("SATISFAIT" if (monotonic_decreasing or monotonic_increasing)
       else "NON SATISFAIT")
)

out("[CRITERE B] Dernier pas <= 1 meV/atome")
out(
    "  -> "
    + ("SATISFAIT" if abs(delta78_mev) <= 1.0 else "NON SATISFAIT")
)

out("[CRITERE C] Plage globale <= 1 meV/atome")
out(
    "  -> "
    + ("SATISFAIT" if global_range_mev <= 1.0 else "NON SATISFAIT")
)

out("[CRITERE D] SCF < 1e-8 Ry")
out(
    "  -> "
    + ("SATISFAIT" if scf_ok else "NON SATISFAIT")
)

out("")

# ============================================================
# 13. CONCLUSION SANS CLASSEMENT AUTOMATIQUE
# ============================================================

out("=" * 78)
out("13. CONCLUSION")
out("=" * 78)

out(
    "[RESULT] La série 4³→8³ ne démontre pas une convergence "
    "énergétique stricte à 1 meV/atome."
)

out(
    "[RESULT] La série est non monotone et présente une plage "
    f"de {global_range_mev:.3f} meV/atome."
)

out(
    "[RESULT] Le calcul 8³ est le maillage le plus dense testé, "
    "mais sa seule densité ne constitue pas une preuve de convergence."
)

out(
    "[RESULT] Les critères SCF sont satisfaits pour les cinq maillages."
)

out(
    "[RESULT] Le choix du maillage de production doit donc être "
    "documenté par une tolérance scientifique explicite."
)

out("")
out(
    "[INFO] Cette phase ne sélectionne pas automatiquement un "
    "maillage comme 'meilleur'."
)

# ============================================================
# 14. PROPOSITION DE SUITE
# ============================================================

out("")
out("=" * 78)
out("14. SUITE RECOMMANDEE")
out("=" * 78)

out(
    "[NEXT] Phase 79.0B : audit ciblé 7³ ↔ 8³ et test de "
    "stabilité électronique."
)

out(
    "[NEXT] Phase 79.0C : définition documentée du maillage "
    "de production."
)

out(
    "[NEXT] Phase 79.1 : génération contrôlée du premier input "
    "DFT de production."
)

out(
    "[INFO] Aucun calcul QE n'est lancé par cette phase."
)

# ============================================================
# 15. PRE-FLIGHT
# ============================================================

out("")
out("=" * 78)
out("15. PRE-FLIGHT")
out("=" * 78)

checks = {
    "5 maillages présents": len(DATA) == 5,
    "SCF < 1e-8 Ry": scf_ok,
    "ecutrho/ecutwfc = 4": math.isclose(560 / 140, 4.0),
    "8³ est le plus dense": DATA[8]["nk_total"] == max(
        d["nk_total"] for d in DATA.values()
    ),
    "série non vide": len(successive) == 4,
}

all_ok = True

for i, (name, status) in enumerate(checks.items(), start=1):
    if status:
        out(f"[OK] CHECK {i} — {name}")
    else:
        out(f"[FAIL] CHECK {i} — {name}")
        all_ok = False

out("")

if all_ok:
    out("[RESULT] PRE-FLIGHT = VALIDÉ")
else:
    out("[RESULT] PRE-FLIGHT = ÉCHEC")

# ============================================================
# 16. RAPPORT
# ============================================================

REPORT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

out("")
out("=" * 78)
out("PHASE 79.0A — FIN")
out("=" * 78)
out(f"[OK] Rapport écrit : {REPORT}")
out("[OK] Aucun fichier scientifique modifié.")
out("[OK] Aucun pw.x exécuté.")

