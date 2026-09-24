import os
import re
from pathlib import Path

os.system("clear")

print("=" * 78)
print("PHASE 78.47 — INPUT-BASED NUMERICAL STABILITY AUDIT")
print("=" * 78)
print("[INFO] READ-ONLY")
print("[INFO] Aucun pw.x")
print("[INFO] Aucun fichier scientifique modifié")
print()

ROOT = Path("/home/hk/HydroMatAI/calculations/new_campaign/TiFeH2")

# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------

def read_text(path):
    try:
        return path.read_text(errors="ignore")
    except Exception:
        return ""

def parse_float(text, pattern):
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    try:
        return float(m.group(1).replace("D", "E").replace("d", "e"))
    except Exception:
        return None

def parse_int(text, pattern):
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def get_energy(out_text):
    # Priorité à la dernière énergie totale QE.
    vals = re.findall(
        r"!\s+total energy\s*=\s*([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)\s+Ry",
        out_text,
        re.I,
    )
    if vals:
        return float(vals[-1].replace("D", "E").replace("d", "e"))

    vals = re.findall(
        r"total energy\s*=\s*([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)\s+Ry",
        out_text,
        re.I,
    )
    if vals:
        return float(vals[-1].replace("D", "E").replace("d", "e"))

    return None

def get_fermi(out_text):
    vals = re.findall(
        r"the Fermi energy is\s+([-+]?\d+(?:\.\d+)?)\s+ev",
        out_text,
        re.I,
    )
    if vals:
        return float(vals[-1])

    vals = re.findall(
        r"EFermi\s*=\s*([-+]?\d+(?:\.\d+)?)",
        out_text,
        re.I,
    )
    if vals:
        return float(vals[-1])

    return None

def is_done(out_text):
    return "JOB DONE." in out_text or "JOB DONE" in out_text

def get_kpoints(text):
    m = re.search(
        r"K_POINTS\s+automatic\s*\n\s*"
        r"(\d+)\s+(\d+)\s+(\d+)\s+"
        r"(\d+)\s+(\d+)\s+(\d+)",
        text,
        re.I,
    )
    if not m:
        return None

    return tuple(int(m.group(i)) for i in range(1, 4))

# ----------------------------------------------------------------------
# Inventaire des INPUTS
# ----------------------------------------------------------------------

inputs = sorted(ROOT.rglob("*.in"))

print("1. INVENTAIRE DES INPUTS")
print("-" * 78)
print(f"Total *.in trouvés : {len(inputs)}")
print()

records = []

for inp in inputs:
    name = inp.name.lower()

    # Exclusion explicite des auxiliaires
    if "kpoints_smearing_0.002ry" in str(inp).lower():
        continue

    text = read_text(inp)

    ecutwfc = parse_float(
        text,
        r"ecutwfc\s*=\s*([-+]?\d+(?:\.\d+)?)",
    )

    degauss = parse_float(
        text,
        r"degauss\s*=\s*([-+]?\d+(?:\.\d+)?)",
    )

    kp = get_kpoints(text)

    # Cherche le .out correspondant
    out = inp.with_suffix(".out")

    if not out.exists():
        # Certains fichiers peuvent avoir un output ailleurs :
        # on ne les retient pas sans correspondance directe.
        continue

    out_text = read_text(out)

    energy = get_energy(out_text)
    fermi = get_fermi(out_text)
    done = is_done(out_text)

    records.append({
        "input": inp,
        "output": out,
        "ecutwfc": ecutwfc,
        "degauss": degauss,
        "kpoints": kp,
        "energy": energy,
        "fermi": fermi,
        "done": done,
    })

print(f"Entrées avec sortie correspondante : {len(records)}")
print()

# ----------------------------------------------------------------------
# Classification stricte
# ----------------------------------------------------------------------

cutoff = {}
kpoints = {}
smearing = {}

for r in records:
    e = r["ecutwfc"]
    d = r["degauss"]
    kp = r["kpoints"]

    # CUTOFF :
    # ecutwfc = 60 / 80 / 100
    # kpoints = 2x2x2
    # degauss = 0.010
    if (
        e in (60.0, 80.0, 100.0)
        and kp == (2, 2, 2)
        and d is not None
        and abs(d - 0.010) < 1e-9
    ):
        cutoff[int(e)] = r

    # KPOINTS :
    # ecutwfc = 60
    # degauss = 0.010
    # kpoints = 2 / 3 / 4
    if (
        e is not None
        and abs(e - 60.0) < 1e-9
        and d is not None
        and abs(d - 0.010) < 1e-9
        and kp in ((2, 2, 2), (3, 3, 3), (4, 4, 4))
    ):
        kpoints[kp] = r

    # SMEARING :
    # ecutwfc = 60
    # kpoints = 2x2x2
    # degauss = .001/.002/.005/.010
    if (
        e is not None
        and abs(e - 60.0) < 1e-9
        and kp == (2, 2, 2)
        and d is not None
        and any(abs(d - x) < 1e-9 for x in (0.001, 0.002, 0.005, 0.010))
    ):
        smearing[round(d, 3)] = r

# ----------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------

def print_series(title, data, ordered_keys):
    print(title)
    print()

    for key in ordered_keys:
        r = data.get(key)

        if r is None:
            print(f"  {key} : [MISSING]")
            continue

        label = key

        if isinstance(key, tuple):
            label = f"{key[0]}x{key[1]}x{key[2]}"

        print(f"  {label}")
        print(f"    INPUT  : {r['input'].name}")
        print(f"    OUTPUT : {r['output'].name}")
        print(f"    ecutwfc: {r['ecutwfc']}")
        print(f"    kpoints: {r['kpoints']}")
        print(f"    degauss: {r['degauss']}")
        print(f"    Energy : {r['energy']}")
        print(f"    Fermi  : {r['fermi']}")
        print(f"    JOB DONE : {r['done']}")
        print()

print("2. SÉRIES PRINCIPALES RETENUES")
print("-" * 78)

print_series(
    "CUTOFF",
    cutoff,
    [60, 80, 100],
)

print_series(
    "KPOINTS",
    kpoints,
    [(2, 2, 2), (3, 3, 3), (4, 4, 4)],
)

print_series(
    "SMEARING",
    smearing,
    [0.001, 0.002, 0.005, 0.010],
)

# ----------------------------------------------------------------------
# Contrôle des quantités
# ----------------------------------------------------------------------

print("3. CONTRÔLE DU NOMBRE DE CALCULS")
print("-" * 78)

print(f"CUTOFF    : {len(cutoff)}/3")
print(f"KPOINTS   : {len(kpoints)}/3")
print(f"SMEARING  : {len(smearing)}/4")

if len(cutoff) != 3 or len(kpoints) != 3 or len(smearing) != 4:
    print("[ERROR] Les séries principales ne sont pas reconstruites.")
    raise SystemExit(1)

print("[OK] Les trois séries principales sont correctement identifiées.")

# ----------------------------------------------------------------------
# Analyse numérique
# ----------------------------------------------------------------------

ENERGY_THRESHOLD = 1e-4
FERMI_THRESHOLD = 1e-2

def analyze(name, data, ordered_keys):
    rows = [data[k] for k in ordered_keys]

    energies = [r["energy"] for r in rows if r["energy"] is not None]
    fermis = [r["fermi"] for r in rows if r["fermi"] is not None]

    done_count = sum(r["done"] for r in rows)

    e_spread = max(energies) - min(energies) if len(energies) == len(rows) else None
    f_spread = max(fermis) - min(fermis) if len(fermis) == len(rows) else None

    stable_energy = e_spread is not None and e_spread <= ENERGY_THRESHOLD
    stable_fermi = f_spread is not None and f_spread <= FERMI_THRESHOLD

    print(name)
    print("-" * 78)

    for key in ordered_keys:
        r = data[key]

        if isinstance(key, tuple):
            label = f"{key[0]}x{key[1]}x{key[2]}"
        else:
            label = str(key)

        print(
            f"{label:>8} | "
            f"E = {r['energy']:.8f} Ry | "
            f"EF = {r['fermi']:.4f} eV | "
            f"JOB DONE = {r['done']}"
        )

    print()
    print(f"Energy spread : {e_spread:.8f} Ry")
    print(f"EF spread     : {f_spread:.4f} eV")
    print(f"Energy seuil  : {ENERGY_THRESHOLD:.1e} Ry")
    print(f"EF seuil      : {FERMI_THRESHOLD:.2e} eV")

    if stable_energy and stable_fermi:
        print("STATUS        : NUMERICAL_STABILITY_ESTABLISHED")
    else:
        print("STATUS        : NUMERICAL_STABILITY_NOT_ESTABLISHED")

    print(f"JOB DONE      : {done_count}/{len(rows)}")
    print()

    return stable_energy and stable_fermi

print()
print("4. ANALYSE DE STABILITÉ")
print("=" * 78)

s_cutoff = analyze(
    "CUTOFF",
    cutoff,
    [60, 80, 100],
)

s_kpoints = analyze(
    "KPOINTS",
    kpoints,
    [(2, 2, 2), (3, 3, 3), (4, 4, 4)],
)

s_smearing = analyze(
    "SMEARING",
    smearing,
    [0.001, 0.002, 0.005, 0.010],
)

# ----------------------------------------------------------------------
# Conclusion
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("5. CONCLUSION GLOBALE")
print("=" * 78)

all_stable = s_cutoff and s_kpoints and s_smearing

print(f"CUTOFF    : {'STABLE' if s_cutoff else 'NOT_ESTABLISHED'}")
print(f"KPOINTS   : {'STABLE' if s_kpoints else 'NOT_ESTABLISHED'}")
print(f"SMEARING  : {'STABLE' if s_smearing else 'NOT_ESTABLISHED'}")
print()

if all_stable:
    print("GLOBAL STATUS : NUMERICAL_STABILITY_ESTABLISHED")
else:
    print("GLOBAL STATUS : NUMERICAL_STABILITY_NOT_ESTABLISHED")

print()
print("[INFO] Aucun calcul QE exécuté.")
print("[INFO] Aucun fichier scientifique modifié.")
print("[INFO] Audit terminé.")
