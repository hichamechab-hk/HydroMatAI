#!/usr/bin/env python3

from pathlib import Path
import math

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")

print("=" * 88)
print("PHASE 79.07 — TRAJECTOIRE K BANDS TiFeH2")
print("=" * 88)
print("[INFO] MODE = ANALYSE / READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun bands.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

# ----------------------------------------------------------------------
# CELLULE RÉELLE FINALE
# ----------------------------------------------------------------------

a = (5.2399261000, 0.0000000000, 0.0000000000)
b = (-0.5935539478, 5.2062000773, 0.0000000000)
c = (0.0000000000, 0.0000000000, 2.6442020000)

def dot(x, y):
    return sum(i*j for i, j in zip(x, y))

def cross(x, y):
    return (
        x[1]*y[2] - x[2]*y[1],
        x[2]*y[0] - x[0]*y[2],
        x[0]*y[1] - x[1]*y[0],
    )

def norm(x):
    return math.sqrt(dot(x, x))

volume = dot(a, cross(b, c))

print("----------------------------------------------------------------------------------------")
print("1. CELLULE DIRECTE")
print("----------------------------------------------------------------------------------------")

print(f"a = {a}")
print(f"b = {b}")
print(f"c = {c}")
print(f"Volume = {abs(volume):.8f} Å³")

print()

# ----------------------------------------------------------------------
# RÉSEAU RÉCIPROQUE
# ----------------------------------------------------------------------

factor = 2.0 * math.pi / volume

astar = tuple(factor*x for x in cross(b, c))
bstar = tuple(factor*x for x in cross(c, a))
cstar = tuple(factor*x for x in cross(a, b))

print("----------------------------------------------------------------------------------------")
print("2. RÉSEAU RÉCIPROQUE")
print("----------------------------------------------------------------------------------------")

print(f"a* = {astar}")
print(f"b* = {bstar}")
print(f"c* = {cstar}")

print()
print(f"|a*| = {norm(astar):.8f} Å⁻¹")
print(f"|b*| = {norm(bstar):.8f} Å⁻¹")
print(f"|c*| = {norm(cstar):.8f} Å⁻¹")

# ----------------------------------------------------------------------
# ANGLES
# ----------------------------------------------------------------------

def angle(u, v):
    x = dot(u, v)/(norm(u)*norm(v))
    x = max(-1.0, min(1.0, x))
    return math.degrees(math.acos(x))

print()
print("----------------------------------------------------------------------------------------")
print("3. GÉOMÉTRIE RÉCIPROQUE")
print("----------------------------------------------------------------------------------------")

print(f"angle(a*,b*) = {angle(astar, bstar):.6f}°")
print(f"angle(b*,c*) = {angle(bstar, cstar):.6f}°")
print(f"angle(c*,a*) = {angle(cstar, astar):.6f}°")

print()
print("----------------------------------------------------------------------------------------")
print("4. POINTS HAUTE SYMÉTRIE — PROPOSITION CONSERVATIVE")
print("----------------------------------------------------------------------------------------")

# Pour la cellule triclinique/monoclinique représentée par ibrav=0,
# on ne suppose pas automatiquement une nomenclature orthorhombique.
# On utilise donc les points conventionnels de la zone de Brillouin
# exprimés dans la base réciproque de la cellule fournie.

kpoints = {
    "G": (0.0, 0.0, 0.0),
    "X": (0.5, 0.0, 0.0),
    "Y": (0.0, 0.5, 0.0),
    "Z": (0.0, 0.0, 0.5),
    "L": (0.5, 0.5, 0.0),
    "M": (0.5, 0.0, 0.5),
    "N": (0.0, 0.5, 0.5),
    "R": (0.5, 0.5, 0.5),
}

for name, k in kpoints.items():
    print(f"{name:>2} = ({k[0]:.3f}, {k[1]:.3f}, {k[2]:.3f})")

print()
print("[WARN] Les noms X/Y/Z/L/M/N/R sont des labels de coordonnées.")
print("[WARN] Ils ne constituent PAS encore une identification officielle")
print("       des points de haute symétrie de la BZ monoclinique.")

# ----------------------------------------------------------------------
# DISTANCES
# ----------------------------------------------------------------------

def cart_k(k):
    return tuple(
        k[0]*astar[i] +
        k[1]*bstar[i] +
        k[2]*cstar[i]
        for i in range(3)
    )

print()
print("----------------------------------------------------------------------------------------")
print("5. DISTANCES RÉCIPROQUES")
print("----------------------------------------------------------------------------------------")

for name, k in kpoints.items():
    q = cart_k(k)
    print(f"{name:>2} : |k| = {norm(q):.8f} Å⁻¹")

# ----------------------------------------------------------------------
# PROPOSITION DE TRAJECTOIRE DE DIAGNOSTIC
# ----------------------------------------------------------------------

print()
print("----------------------------------------------------------------------------------------")
print("6. TRAJECTOIRE DE DIAGNOSTIC")
print("----------------------------------------------------------------------------------------")

path = ["G", "X", "L", "Y", "G", "Z", "M", "R", "N", "Z"]

print(" → ".join(path))

print()
print("[INFO] Cette trajectoire est uniquement DIAGNOSTIQUE.")
print("[INFO] Elle ne doit pas encore être utilisée comme trajectoire")
print("       'haute symétrie publiée' dans un article.")

print()
print("========================================================================================")
print("DÉCISION PHASE 79.07")
print("========================================================================================")
print("[RESULT] Réseau réciproque calculé à partir de la cellule finale.")
print("[RESULT] Aucune hypothèse de nomenclature de BZ n'est présentée comme certaine.")
print("[NEXT] Avant bands.x final : valider la BZ et la trajectoire haute symétrie")
print("       avec la symétrie cristallographique réelle.")
print("=" * 88)
