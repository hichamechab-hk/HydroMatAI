from pathlib import Path
import re

ROOT = Path("/home/hk/HydroMatAI")
BASE = ROOT / "calculations" / "new_campaign" / "TiFeH2"

print("=" * 78)
print("PHASE 78.23 — AUDIT CORRECTIF READ-ONLY")
print("=" * 78)
print("[INFO] Aucun pw.x ne sera exécuté")
print("[INFO] Aucun input/output QE ne sera modifié")
print()

# ----------------------------------------------------------------------
# 1. INPUTS PRINCIPAUX
# ----------------------------------------------------------------------

inputs = {
    "CUTOFF": [
        BASE / "convergence/cutoff_60Ry_2x2x2.in",
        BASE / "convergence/cutoff_80Ry_2x2x2.in",
        BASE / "convergence/cutoff_100Ry_2x2x2.in",
    ],
    "KPOINTS": [
        BASE / "convergence/kpoints_2x2x2_60Ry.in",
        BASE / "convergence/kpoints_3x3x3_60Ry.in",
        BASE / "convergence/kpoints_4x4x4_60Ry.in",
    ],
    "SMEARING": [
        BASE / "convergence/smearing_tests/degauss_0.001Ry/TiFeH2_degauss_0.001Ry.in",
        BASE / "convergence/smearing_tests/degauss_0.002Ry/TiFeH2_degauss_0.002Ry.in",
        BASE / "convergence/smearing_tests/degauss_0.005Ry/TiFeH2_degauss_0.005Ry.in",
        BASE / "convergence/smearing_tests/degauss_0.010Ry/TiFeH2_degauss_0.010Ry.in",
    ],
}

# ----------------------------------------------------------------------
# 2. EXTRACTION GENERIQUE
# ----------------------------------------------------------------------

def read(path):
    return path.read_text(errors="replace")


def first_float(pattern, text, flags=re.I | re.M):
    m = re.search(pattern, text, flags)
    if not m:
        return None
    try:
        return float(m.group(1).replace("D", "E").replace("d", "e"))
    except ValueError:
        return None


def parameter(text, name):
    pat = rf"\b{name}\s*=\s*([^\s,/\n]+)"
    m = re.search(pat, text, re.I)
    return m.group(1).strip() if m else None


# ----------------------------------------------------------------------
# 3. PHASE 78.23A — PSEUDO_DIR
# ----------------------------------------------------------------------

print("=" * 78)
print("PHASE 78.23A — AUDIT PSEUDO_DIR")
print("=" * 78)

pseudo_dirs = {}

for group, paths in inputs.items():
    print(f"\n--- {group} ---")
    for p in paths:
        if not p.exists():
            print(f"[FAIL] Input absent : {p}")
            continue

        text = read(p)
        m = re.search(
            r"pseudo_dir\s*=\s*['\"]([^'\"]+)['\"]",
            text,
            re.I,
        )

        value = m.group(1) if m else "<ABSENT>"
        pseudo_dirs.setdefault(group, set()).add(value)

        print(f"{p.name}: pseudo_dir = {value}")

for group, values in pseudo_dirs.items():
    if len(values) == 1:
        print(f"[OK] {group}: pseudo_dir cohérent")
    else:
        print(f"[WARN] {group}: pseudo_dir varie : {sorted(values)}")


# ----------------------------------------------------------------------
# 4. PHASE 78.23B — CELL / ATOMIC BLOCKS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.23B — COMPARAISON RÉELLE DE LA GÉOMÉTRIE")
print("=" * 78)


def extract_block(text, start_token, end_tokens):
    lines = text.splitlines()

    start = None
    for i, line in enumerate(lines):
        if line.strip().upper().startswith(start_token.upper()):
            start = i
            break

    if start is None:
        return None

    block = [lines[start].strip()]

    for line in lines[start + 1:]:
        stripped = line.strip()

        if any(
            stripped.upper().startswith(token.upper())
            for token in end_tokens
        ):
            break

        if stripped:
            block.append(stripped)

    return tuple(block)


end_tokens = [
    "ATOMIC_POSITIONS",
    "K_POINTS",
    "CELL_PARAMETERS",
    "OCCUPATIONS",
    "&",
]

for group, paths in inputs.items():
    print(f"\n--- {group} ---")

    geometries = []

    for p in paths:
        if not p.exists():
            continue

        text = read(p)

        cell = extract_block(
            text,
            "CELL_PARAMETERS",
            end_tokens,
        )

        atomic = extract_block(
            text,
            "ATOMIC_POSITIONS",
            end_tokens,
        )

        geometries.append((p.name, cell, atomic))

    if not geometries:
        print("[FAIL] Aucune géométrie trouvée")
        continue

    ref_name, ref_cell, ref_atomic = geometries[0]

    all_cell_same = True
    all_atomic_same = True

    for name, cell, atomic in geometries:
        cell_same = cell == ref_cell
        atomic_same = atomic == ref_atomic

        print(
            f"{name}: "
            f"CELL={'IDENTIQUE' if cell_same else 'DIFFÉRENTE'} | "
            f"ATOMIC={'IDENTIQUE' if atomic_same else 'DIFFÉRENTE'}"
        )

        if not cell_same:
            all_cell_same = False
        if not atomic_same:
            all_atomic_same = False

    if all_cell_same:
        print("[OK] CELL_PARAMETERS identiques dans la série")
    else:
        print(
            "[INFO] CELL_PARAMETERS diffèrent — "
            "à vérifier si différence intentionnelle"
        )

    if all_atomic_same:
        print("[OK] ATOMIC_POSITIONS identiques dans la série")
    else:
        print(
            "[INFO] ATOMIC_POSITIONS diffèrent — "
            "à vérifier si différence intentionnelle"
        )


# ----------------------------------------------------------------------
# 5. PHASE 78.23C — DIAGNOSTIC SCF ACCURACY
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.23C — DIAGNOSTIC DU PARSER SCF ACCURACY")
print("=" * 78)

output_paths = [
    BASE / "convergence/run_60Ry/TiFeH2_cutoff_60.out",
    BASE / "convergence/run_80Ry/TiFeH2_cutoff_80.out",
    BASE / "convergence/run_100Ry/TiFeH2_cutoff_100.out",
    BASE / "convergence/run_kpoints_2x2x2/TiFeH2_kpoints_2.out",
    BASE / "convergence/run_kpoints_3x3x3/TiFeH2_kpoints_3.out",
    BASE / "convergence/run_kpoints_4x4x4/TiFeH2_kpoints_4.out",
    BASE / "convergence/smearing_tests/degauss_0.001Ry/TiFeH2_degauss_0.001Ry.out",
    BASE / "convergence/smearing_tests/degauss_0.002Ry/TiFeH2_degauss_0.002Ry.out",
    BASE / "convergence/smearing_tests/degauss_0.005Ry/TiFeH2_degauss_0.005Ry.out",
    BASE / "convergence/smearing_tests/degauss_0.010Ry/TiFeH2_degauss_0.010Ry.out",
]

for p in output_paths:
    print(f"\n--- {p.name} ---")

    if not p.exists():
        print("[FAIL] Output absent")
        continue

    text = read(p)
    lines = text.splitlines()

    matches = []

    for i, line in enumerate(lines, start=1):
        low = line.lower()

        if (
            "estimated scf accuracy" in low
            or "convergence has been achieved" in low
            or "convergence NOT achieved" in low
            or "convergence not achieved" in low
        ):
            matches.append((i, line.strip()))

    if not matches:
        print("[WARN] Aucun marqueur SCF explicite trouvé")
    else:
        for i, line in matches[-5:]:
            print(f"{i}: {line}")

    # Cherche spécifiquement une valeur associée à
    # "estimated scf accuracy"
    for i, line in enumerate(lines, start=1):
        if "estimated scf accuracy" in line.lower():
            print(f"[SCF ACCURACY RAW] line {i}: {line.strip()}")

            nums = re.findall(
                r"[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?",
                line,
            )

            print(f"[NUMBERS DETECTED] {nums}")


# ----------------------------------------------------------------------
# 6. PHASE 78.23D — INVENTAIRE RÉEL DOS / BANDS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.23D — INVENTAIRE RÉEL DOS / BANDS")
print("=" * 78)

all_files = [
    p for p in BASE.rglob("*")
    if p.is_file()
]

dos_candidates = []
bands_candidates = []

for p in all_files:
    name = p.name.lower()
    path_str = str(p).lower()

    if "dos" in name or "/dos/" in path_str:
        dos_candidates.append(p)

    if "band" in name or "/bands/" in path_str:
        bands_candidates.append(p)

print()
print(f"DOS candidats   : {len(dos_candidates)}")

for p in sorted(dos_candidates):
    print(f"  {p.relative_to(ROOT)}")

print()
print(f"BANDS candidats : {len(bands_candidates)}")

for p in sorted(bands_candidates):
    print(f"  {p.relative_to(ROOT)}")


# ----------------------------------------------------------------------
# 7. PHASE 78.23E — MARQUEURS DOS / BANDS DANS OUTPUTS
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.23E — MARQUEURS ÉLECTRONIQUES")
print("=" * 78)

electronic_markers = {
    "DOS": [
        "DOS",
        "dosup",
        "dosdw",
        "EFermi",
        "Fermi energy",
    ],
    "BANDS": [
        "bands",
        "End of band structure calculation",
        "number of k points",
    ],
}

for category, markers in electronic_markers.items():
    print(f"\n--- {category} ---")

    found = []

    for p in all_files:
        if p.suffix.lower() not in {".out", ".dat", ".gnu", ".txt"}:
            continue

        try:
            text = read(p)
        except Exception:
            continue

        for marker in markers:
            if marker.lower() in text.lower():
                found.append((p, marker))

    unique = {}
    for p, marker in found:
        unique.setdefault(p, set()).add(marker)

    if not unique:
        print("[INFO] Aucun marqueur trouvé")
    else:
        for p, markers_found in sorted(unique.items()):
            print(
                f"{p.relative_to(ROOT)} : "
                f"{', '.join(sorted(markers_found))}"
            )


# ----------------------------------------------------------------------
# 8. PHASE 78.23F — RÉSUMÉ
# ----------------------------------------------------------------------

print()
print("=" * 78)
print("PHASE 78.23F — SYNTHÈSE")
print("=" * 78)

print("[OK] Audit pseudo_dir effectué")
print("[OK] Comparaison réelle CELL_PARAMETERS / ATOMIC_POSITIONS effectuée")
print("[OK] Diagnostic SCF accuracy effectué")
print("[OK] Inventaire récursif DOS effectué")
print("[OK] Inventaire récursif BANDS effectué")
print("[OK] Recherche de marqueurs électroniques effectuée")

print()
print("[IMPORTANT]")
print("Cette phase est READ-ONLY.")
print("Aucun pw.x n'a été exécuté.")
print("Aucun input QE n'a été modifié.")
print("Aucun output QE n'a été modifié.")
print("Aucune donnée scientifique n'a été recalculée.")

print()
print("=" * 78)
print("PHASE 78.23 TERMINÉE")
print("=" * 78)
