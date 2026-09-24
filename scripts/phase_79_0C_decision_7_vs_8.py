#!/usr/bin/env python3

from pathlib import Path

print("\033[2J\033[H", end="")

print("=" * 78)
print("PHASE 79.0C — AUDIT DECISIONNEL DU MAILLAGE 7³ ↔ 8³")
print("=" * 78)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print()

ROOT = Path("/home/hk/HydroMatAI")

# Données vérifiées par les phases 78.64 / 78.90 / 79.0A / 79.0B
DATA = {
    "7³": {
        "energy": -880.7491986800,
        "fermi": 12.9245,
        "smearing_ry": 0.00006075,
        "scf": 5.8e-9,
        "nk_total": 343,
        "nk_irr": 100,
        "cbands": 11,
        "iterations": 18,
        "job_done": True,
    },
    "8³": {
        "energy": -880.7460030600,
        "fermi": 12.9621,
        "smearing_ry": -0.00014068,
        "scf": 7.5e-9,
        "nk_total": 512,
        "nk_irr": 170,
        "cbands": 10,
        "iterations": 19,
        "job_done": True,
    },
}

NAT = 8
RY_TO_MEV = 13605.693009
SCF_TOL = 1e-8

e7 = DATA["7³"]["energy"]
e8 = DATA["8³"]["energy"]

ef7 = DATA["7³"]["fermi"]
ef8 = DATA["8³"]["fermi"]

ts7 = DATA["7³"]["smearing_ry"]
ts8 = DATA["8³"]["smearing_ry"]

de_ry = e8 - e7
de_mev_atom = de_ry * RY_TO_MEV / NAT

def_mev = ef8 - ef7

dts_ry = ts8 - ts7
dts_mev_atom = dts_ry * RY_TO_MEV / NAT

print("===== 1. DONNEES DE REFERENCE =====")
print("-" * 78)

print(f"7³ : E = {e7:.10f} Ry")
print(f"8³ : E = {e8:.10f} Ry")
print(f"7³ : EF = {ef7:.4f} eV")
print(f"8³ : EF = {ef8:.4f} eV")
print(f"7³ : SCF = {DATA['7³']['scf']:.3e} Ry")
print(f"8³ : SCF = {DATA['8³']['scf']:.3e} Ry")
print()

print("===== 2. DIFFERENCES 7³ → 8³ =====")
print("-" * 78)

print(f"ΔE cellule       = {de_ry:+.10f} Ry")
print(f"ΔE / atome       = {de_mev_atom:+.6f} meV/at")
print(f"ΔEF              = {def_mev:+.6f} eV")
print(f"Δ(-TS)           = {dts_ry:+.10f} Ry")
print(f"Δ(-TS) / atome   = {dts_mev_atom:+.6f} meV/at")
print()

print("===== 3. CRITERES DE VALIDATION =====")
print("-" * 78)

criteria = []

# A — convergence énergétique stricte à 1 meV/at
A = abs(de_mev_atom) <= 1.0
criteria.append(("A", "ΔE ≤ 1 meV/at", A))
print(f"[{'PASS' if A else 'FAIL'}] A : |ΔE| ≤ 1 meV/at")

# B — tolérance intermédiaire à 5 meV/at
B = abs(de_mev_atom) <= 5.0
criteria.append(("B", "ΔE ≤ 5 meV/at", B))
print(f"[{'PASS' if B else 'FAIL'}] B : |ΔE| ≤ 5 meV/at")

# C — tolérance à 10 meV/at
C = abs(de_mev_atom) <= 10.0
criteria.append(("C", "ΔE ≤ 10 meV/at", C))
print(f"[{'PASS' if C else 'FAIL'}] C : |ΔE| ≤ 10 meV/at")

# D — convergence SCF
D = (
    DATA["7³"]["scf"] < SCF_TOL
    and DATA["8³"]["scf"] < SCF_TOL
)
criteria.append(("D", "SCF < 1e-8 Ry", D))
print(f"[{'PASS' if D else 'FAIL'}] D : SCF < 1e-8 Ry")

# E — calculs terminés
E = DATA["7³"]["job_done"] and DATA["8³"]["job_done"]
criteria.append(("E", "JOB DONE 7³ et 8³", E))
print(f"[{'PASS' if E else 'FAIL'}] E : JOB DONE")

print()

print("===== 4. EFFET DU SMEARING =====")
print("-" * 78)

print(
    f"|Δ(-TS)| = {abs(dts_mev_atom):.6f} meV/at"
)
print(
    f"|ΔE totale| = {abs(de_mev_atom):.6f} meV/at"
)

if abs(dts_mev_atom) < abs(de_mev_atom):
    print("[RESULT] La variation du terme (-TS) est plus faible que ΔE total.")
    print("[RESULT] Le smearing seul n'explique donc pas la variation énergétique.")
else:
    print("[INFO] Le terme (-TS) est du même ordre ou supérieur à ΔE.")

print()

print("===== 5. QUALITE NUMERIQUE DES DEUX CALCULS =====")
print("-" * 78)

for mesh in ("7³", "8³"):
    d = DATA[mesh]

    print(
        f"{mesh} : Nk_total={d['nk_total']} | "
        f"Nk_irr={d['nk_irr']} | "
        f"SCF={d['scf']:.2e} | "
        f"c_bands={d['cbands']} | "
        f"iterations={d['iterations']} | "
        f"JOB_DONE={d['job_done']}"
    )

print()

print("===== 6. INTERPRETATION DECISIONNELLE =====")
print("-" * 78)

if A:
    print("[RESULT] CONVERGENCE ENERGETIQUE STRICTE : 1 meV/at SATISFAITE.")
else:
    print("[RESULT] CONVERGENCE ENERGETIQUE STRICTE : 1 meV/at NON SATISFAITE.")

if B:
    print("[RESULT] Une tolérance de 5 meV/at est satisfaite.")
else:
    print("[RESULT] Une tolérance de 5 meV/at est NON satisfaite.")

if C:
    print("[RESULT] Une tolérance de 10 meV/at est satisfaite.")

print()

print("===== 7. DECISION SUR 8³ =====")
print("-" * 78)

print("[INFO] 8³ est le maillage le plus dense effectivement calculé.")
print("[INFO] 8³ contient 512 k-points totaux et 170 irréductibles.")
print("[INFO] 7³ contient 343 k-points totaux et 100 irréductibles.")
print()

if A:
    print("[DECISION] 8³ peut être retenu avec convergence énergétique à 1 meV/at.")
elif B:
    print(
        "[DECISION] 8³ peut être retenu comme maillage de production "
        "si une tolérance de 5 meV/at est explicitement adoptée."
    )
elif C:
    print(
        "[DECISION] 8³ peut être retenu uniquement avec une tolérance "
        "explicite de 10 meV/at."
    )
else:
    print(
        "[DECISION] Aucune des tolérances 1/5/10 meV/at n'est satisfaite."
    )

print()
print("[IMPORTANT]")
print("La densité 8³ ne constitue pas, à elle seule, une preuve de convergence.")
print("La justification du maillage doit indiquer explicitement la tolérance")
print("énergétique choisie et les résultats 7³ → 8³.")

print()

print("===== 8. RECOMMANDATION POUR LE PROTOCOLE REPRODUCTIBLE =====")
print("-" * 78)

print("[OK] ecutwfc = 140 Ry")
print("[OK] ecutrho = 560 Ry")
print("[OK] nspin = 2")
print("[OK] smearing = Marzari-Vanderbilt")
print("[OK] degauss = 0.01 Ry")
print("[OK] conv_thr < 1e-8 Ry")
print("[OK] 7³ et 8³ terminés avec JOB DONE")
print()

print("[INFO] Le choix final du maillage doit rester lié à la tolérance")
print("[INFO] énergétique explicitement déclarée dans le protocole.")
print()

print("===== 9. CONCLUSION =====")
print("-" * 78)

print(
    f"7³ → 8³ : ΔE = {de_mev_atom:+.6f} meV/at ; "
    f"ΔEF = {def_mev:+.6f} eV."
)

if not A:
    print(
        "[CONCLUSION] Les données ne permettent pas de déclarer une "
        "convergence stricte à 1 meV/at."
    )

if B:
    print(
        "[CONCLUSION] Une tolérance de 5 meV/at est presque atteinte mais "
        "n'est pas satisfaite ici : 5.434828 meV/at."
    )

if C:
    print(
        "[CONCLUSION] Une tolérance de 10 meV/at est satisfaite."
    )

print(
    "[CONCLUSION] Le résultat 8³ doit donc être présenté comme le maillage "
    "le plus dense testé, et non comme une preuve automatique de convergence."
)

print()
print("=" * 78)
print("PHASE 79.0C — FIN")
print("=" * 78)
print("[INFO] Audit décisionnel terminé.")
print("[INFO] Aucun pw.x exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
