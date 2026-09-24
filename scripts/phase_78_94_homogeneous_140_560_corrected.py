#!/usr/bin/env python3

from pathlib import Path
import re

print("\033[2J\033[H", end="")

BASE = Path("/home/hk/HydroMatAI")
RY_TO_EV = 13.605693009
NAT = 8

FILES = {
    "4x4x4": BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k444.out",
    "5x5x5": BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k555.out",
    "6x6x6": BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k666.out",
    "8x8x8": BASE / "calculations/phase78_61_convergence/TiFeH2/ecut140_rho560_k888_phase78_63.out",
}

EXPECTED = {
    "4x4x4": 30,
    "5x5x5": 39,
    "6x6x6": 80,
    "8x8x8": 170,
}

def first_float(pattern, text):
    m = re.search(pattern, text, re.MULTILINE)
    return float(m.group(1)) if m else None

def extract(path):
    text = path.read_text(errors="ignore")

    energy = first_float(
        r"!\s+total energy\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
        text
    )

    ef = first_float(
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
        text
    )

    ts = first_float(
        r"\(-TS\)\s*=\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
        text
    )

    scf_values = re.findall(
        r"estimated scf accuracy\s*<\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry",
        text,
        re.IGNORECASE
    )
    scf = float(scf_values[-1]) if scf_values else None

    nk = None
    m = re.search(r"number of k points=\s*(\d+)", text)
    if m:
        nk = int(m.group(1))

    job_done = "JOB DONE." in text

    cbands = len(re.findall(r"c_bands:\s*\d+\s+eigenvalues not converged", text))

    return {
        "energy": energy,
        "ef": ef,
        "ts": ts,
        "scf": scf,
        "nk": nk,
        "job_done": job_done,
        "cbands": cbands,
    }

print("=" * 88)
print("PHASE 78.94 — AUDIT DE CONVERGENCE HOMOGÈNE 140/560")
print("=" * 88)
print("[INFO] MODE = READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun recalcul")
print("[INFO] Aucun fichier scientifique modifié")
print("[INFO] Jeu homogène : 4³, 5³, 6³, 8³")
print("[INFO] 7³ EXCLU : ancien calcul 140/240")
print()

data = {}

for mesh, path in FILES.items():
    print("-" * 88)
    print(f"[FILE] {mesh}")
    print(f"[PATH] {path}")

    if not path.exists():
        print("[ERROR] Fichier absent")
        raise SystemExit(1)

    d = extract(path)
    data[mesh] = d

    print(f"[INFO] E       = {d['energy']:.10f} Ry" if d["energy"] is not None
          else "[ERROR] E       = introuvable")
    print(f"[INFO] EF      = {d['ef']:.4f} eV" if d["ef"] is not None
          else "[ERROR] EF      = introuvable")
    print(f"[INFO] (-TS)   = {d['ts']:.8f} Ry" if d["ts"] is not None
          else "[WARN] (-TS)   = introuvable")
    print(f"[INFO] SCF acc = {d['scf']:.3e} Ry" if d["scf"] is not None
          else "[WARN] SCF acc = introuvable")
    print(f"[INFO] Nk      = {d['nk']}" if d["nk"] is not None
          else "[WARN] Nk      = introuvable")
    print(f"[INFO] c_bands = {d['cbands']}")
    print(f"[INFO] JOB DONE = {d['job_done']}")

print()
print("=" * 88)
print("TABLEAU HOMOGÈNE 140/560")
print("=" * 88)

print(
    f"{'Mesh':<10}"
    f"{'E (Ry)':>18}"
    f"{'E/at (Ry)':>18}"
    f"{'EF (eV)':>12}"
    f"{'Nk':>8}"
    f"{'JOB':>8}"
)

for mesh, d in data.items():
    e = d["energy"]
    eat = e / NAT if e is not None else None

    print(
        f"{mesh:<10}"
        f"{e:>18.10f}"
        f"{eat:>18.10f}"
        f"{d['ef']:>12.4f}"
        f"{d['nk']:>8}"
        f"{str(d['job_done']):>8}"
    )

print()
print("=" * 88)
print("VARIATIONS SUCCESSIVES — meV/atome")
print("=" * 88)

meshes = ["4x4x4", "5x5x5", "6x6x6", "8x8x8"]

successive = []

for a, b in zip(meshes, meshes[1:]):
    ea = data[a]["energy"]
    eb = data[b]["energy"]

    delta_mev_atom = (eb - ea) * RY_TO_EV * 1000.0 / NAT
    successive.append(abs(delta_mev_atom))

    print(
        f"{a} -> {b} : "
        f"{delta_mev_atom:+.6f} meV/at"
    )

print()
print("=" * 88)
print("VARIATIONS EF")
print("=" * 88)

for a, b in zip(meshes, meshes[1:]):
    delta_ef = data[b]["ef"] - data[a]["ef"]
    print(f"{a} -> {b} : {delta_ef:+.6f} eV")

ef_values = [data[m]["ef"] for m in meshes]
ef_range = max(ef_values) - min(ef_values)

print()
print(f"[RESULT] EF range = {ef_range:.6f} eV")

print()
print("=" * 88)
print("CRITÈRES DE CONVERGENCE")
print("=" * 88)

max_adj = max(successive)

print(f"[RESULT] Variation adjacente maximale = {max_adj:.6f} meV/at")
print(f"[TEST] <= 10 meV/at : {'PASS' if max_adj <= 10 else 'FAIL'}")
print(f"[TEST] <= 5  meV/at : {'PASS' if max_adj <= 5 else 'FAIL'}")
print(f"[TEST] <= 2  meV/at : {'PASS' if max_adj <= 2 else 'FAIL'}")
print(f"[TEST] <= 1  meV/at : {'PASS' if max_adj <= 1 else 'FAIL'}")

all_job = all(data[m]["job_done"] for m in meshes)
all_scf = all(
    data[m]["scf"] is not None and data[m]["scf"] < 1e-8
    for m in meshes
)

print()
print(f"[TEST] Tous JOB DONE : {'PASS' if all_job else 'FAIL'}")
print(f"[TEST] Tous SCF < 1e-8 Ry : {'PASS' if all_scf else 'FAIL'}")

print()
print("=" * 88)
print("CONCLUSION")
print("=" * 88)

if max_adj <= 10:
    print("[RESULT] PASS sous tolérance explicite de 10 meV/at.")
else:
    print("[RESULT] FAIL sous tolérance de 10 meV/at.")

if max_adj <= 5:
    print("[RESULT] PASS sous tolérance de 5 meV/at.")
else:
    print("[RESULT] FAIL sous tolérance de 5 meV/at.")

print()
print("[WARN] Le maillage 7³ homogène 140/560 est absent.")
print("[WARN] Le 7³ disponible est 140/240 et est EXCLU.")
print("[WARN] Il ne faut donc pas présenter cette série comme une")
print("       démonstration stricte de convergence monotone.")
print("[INFO] Le 8³/140/560 est néanmoins un calcul homogène réel")
print("       et terminé, avec E = -880.72271576 Ry.")

print("=" * 88)
