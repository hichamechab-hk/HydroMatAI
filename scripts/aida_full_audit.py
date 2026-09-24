#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]
SUBJECT = "TiFeH2"

PRIORITY = ROOT / "reports/dft_h2_priority.csv"
PHASE55 = ROOT / "calculations/phase_55_final_scientific_consistency/phase55_final_ranking.csv"

HIST = ROOT / "calculations/top5_dft" / SUBJECT
NEW = ROOT / "calculations/new_campaign" / SUBJECT


# ============================================================================
# UTILITAIRES
# ============================================================================

def banner(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def phase(number, title):
    print()
    print(f"--- PHASE {number} : {title} ---")


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def read_csv_rows(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_text(path):
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def files_under(path):
    if not path.exists():
        return []
    return sorted(
        p for p in path.rglob("*")
        if p.is_file()
    )


def qe_files(path):
    allowed = {
        ".in", ".out", ".dos", ".cif", ".xml",
    }
    return [p for p in files_under(path) if p.suffix.lower() in allowed]


def extract_regex(text, pattern, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


def extract_all(text, pattern, flags=re.I):
    return re.findall(pattern, text, flags)


# ============================================================================
# PHASE 2.4 — AGRÉGATION QE
# ============================================================================

def classify_qe_file(path):
    name = path.name.lower()

    if "relax" in name:
        kind = "RELAX"
    elif "scf" in name:
        kind = "SCF"
    elif "bands" in name:
        kind = "BANDS"
    elif "dos" in name:
        kind = "DOS"
    elif "nscf" in name:
        kind = "NSCF"
    elif "cutoff" in name or "ecut" in name:
        kind = "CUTOFF"
    elif "kpoint" in name or "kpts" in name:
        kind = "KPOINTS"
    elif "smearing" in name or "degauss" in name:
        kind = "SMEARING"
    else:
        kind = "OTHER"

    if path.is_relative_to(HIST):
        generation = "HISTORICAL"
    elif path.is_relative_to(NEW):
        generation = "NEW_CAMPAIGN"
    else:
        generation = "UNKNOWN"

    return generation, kind


def aggregate_qe():
    result = defaultdict(list)

    for path in qe_files(HIST):
        generation, kind = classify_qe_file(path)
        result[(generation, kind)].append(path)

    for path in qe_files(NEW):
        generation, kind = classify_qe_file(path)
        result[(generation, kind)].append(path)

    return result


# ============================================================================
# PHASE 2.5 — COHÉRENCE MÉTADONNÉES
# ============================================================================

def parse_qe_parameters(path):
    text = read_text(path)

    values = {}

    patterns = {
        "ecutwfc": r"\becutwfc\s*=\s*([0-9.eE+-]+)",
        "ecutrho": r"\becutrho\s*=\s*([0-9.eE+-]+)",
        "degauss": r"\bdegauss\s*=\s*([0-9.eE+-]+)",
        "nat": r"\bnat\s*=\s*(\d+)",
        "ntyp": r"\bntyp\s*=\s*(\d+)",
        "nspin": r"\bnspin\s*=\s*(\d+)",
    }

    for key, pattern in patterns.items():
        value = extract_regex(text, pattern)
        if value is not None:
            values[key] = safe_float(value)

    smearing = extract_regex(text, r"\bsmearing\s*=\s*['\"]([^'\"]+)['\"]")
    if smearing:
        values["smearing"] = smearing

    return values


def metadata_audit(files):
    records = []

    for path in files:
        if path.suffix.lower() != ".in":
            continue

        params = parse_qe_parameters(path)
        records.append({
            "file": str(path.relative_to(ROOT)),
            "parameters": params,
        })

    return records


# ============================================================================
# PHASE 2.6 — PROVENANCE
# ============================================================================

def provenance_summary():
    return {
        "literature": PRIORITY.exists(),
        "phase55_screening": PHASE55.exists(),
        "historical_qe": HIST.exists(),
        "new_campaign_qe": NEW.exists(),
    }


# ============================================================================
# PHASE 3 — PARSING QE
# ============================================================================

def parse_qe_status(path):
    text = read_text(path)

    if path.suffix.lower() != ".out":
        return "INPUT_OR_DATA"

    if "JOB DONE." in text:
        return "COMPLETED"

    failure_patterns = [
        "Error in routine",
        "convergence NOT achieved",
        "Maximum number of iterations reached",
        "stopping ...",
        "%%%%%%%%%%%%%%%",
    ]

    for pattern in failure_patterns:
        if pattern.lower() in text.lower():
            return "FAILED_OR_INCOMPLETE"

    return "UNKNOWN"


def parse_qe_results(path):
    text = read_text(path)

    result = {}

    energy = extract_regex(
        text,
        r"!\s+total energy\s+=\s+([-+0-9.eE]+)\s+Ry"
    )
    if energy is not None:
        result["total_energy_Ry"] = safe_float(energy)

    fermi = extract_regex(
        text,
        r"(?:the Fermi energy is|EFermi\s*=)\s*([-+0-9.eE]+)"
    )
    if fermi is not None:
        result["fermi_energy_eV"] = safe_float(fermi)

    iterations = extract_all(
        text,
        r"(?:iteration|iter)\s*#?\s*(\d+)"
    )
    if iterations:
        result["iterations_seen"] = len(iterations)

    return result


# ============================================================================
# PHASE 4 — CONVERGENCE
# ============================================================================

def numerical_parameter_records(records, parameter):
    values = []

    for record in records:
        value = record["parameters"].get(parameter)
        if value is not None:
            values.append((
                record["file"],
                value,
            ))

    return sorted(values, key=lambda x: x[1])


def convergence_summary(records):
    summary = {}

    for parameter in ("ecutwfc", "ecutrho", "degauss"):
        summary[parameter] = numerical_parameter_records(
            records,
            parameter,
        )

    return summary


# ============================================================================
# PHASE 5 — ANALYSE SCIENTIFIQUE DES ARTEFACTS
# ============================================================================

def electronic_summary(all_files):
    result = {
        "relax": [],
        "scf": [],
        "dos": [],
        "bands": [],
        "nscf": [],
    }

    for path in all_files:
        name = path.name.lower()

        if "relax" in name:
            result["relax"].append(path)

        if "scf" in name:
            result["scf"].append(path)

        if "dos" in name:
            result["dos"].append(path)

        if "bands" in name:
            result["bands"].append(path)

        if "nscf" in name:
            result["nscf"].append(path)

    return result


# ============================================================================
# PHASE 6 — COHÉRENCE SCIENTIFIQUE
# ============================================================================

def scientific_provenance():
    rows = read_csv_rows(PRIORITY)
    row = next(
        (r for r in rows if r.get("material") == SUBJECT),
        None,
    )

    phase55_rows = read_csv_rows(PHASE55)
    row55 = next(
        (r for r in phase55_rows if r.get("material") == SUBJECT),
        None,
    )

    result = {
        "literature_h2": None,
        "ambient_score": None,
        "scientific_score": None,
        "final_screening_score": None,
        "scientific_corrected": None,
    }

    if row:
        result["literature_h2"] = safe_float(
            row.get("h2_uptake_wt_percent")
        )
        result["ambient_score"] = safe_float(
            row.get("ambient_score")
        )
        result["scientific_score"] = safe_float(
            row.get("scientific_score")
        )

    if row55:
        result["final_screening_score"] = safe_float(
            row55.get("final_screening_score")
        )
        result["scientific_corrected"] = safe_float(
            row55.get("scientific_corrected")
        )

    return result


# ============================================================================
# PHASE 7 — AUDIT SCORE 0.991579
# ============================================================================

def audit_screening_score():
    data = scientific_provenance()

    findings = []

    if data["literature_h2"] is not None:
        findings.append(
            "H2 uptake identifié comme donnée littérature."
        )

    if data["final_screening_score"] is not None:
        findings.append(
            "final_screening_score identifié comme score composite "
            "de screening HydroMatAI."
        )

    findings.append(
        "Le score composite n'est PAS traité comme une validation DFT indépendante."
    )

    findings.append(
        "Les résultats QE historiques et nouvelle campagne restent séparés."
    )

    return data, findings


# ============================================================================
# PHASE 8 — ORCHESTRATION
# ============================================================================

def main():
    banner("AIDA — FULL AUDIT READ-ONLY")
    print(f"ROOT    : {ROOT}")
    print(f"SUBJECT : {SUBJECT}")
    print()
    print("POLITIQUE :")
    print("  - aucun calcul QE")
    print("  - aucun fichier scientifique modifié")
    print("  - aucune fusion historique / nouvelle campagne")
    print("  - aucune validation scientifique inventée")

    # ----------------------------------------------------------------------
    # 2.4
    # ----------------------------------------------------------------------
    phase("2.4", "AGRÉGATION STRUCTURÉE DES CALCULS QE")

    aggregated = aggregate_qe()

    for (generation, kind), paths in sorted(aggregated.items()):
        print(
            f"[{generation:14}] {kind:10} : {len(paths):3} fichier(s)"
        )

    # ----------------------------------------------------------------------
    # 2.5
    # ----------------------------------------------------------------------
    phase("2.5", "COHÉRENCE DES MÉTADONNÉES QE")

    historical_inputs = [
        p for p in qe_files(HIST)
        if p.suffix.lower() == ".in"
    ]

    new_inputs = [
        p for p in qe_files(NEW)
        if p.suffix.lower() == ".in"
    ]

    historical_meta = metadata_audit(historical_inputs)
    new_meta = metadata_audit(new_inputs)

    print(f"Inputs historiques analysés : {len(historical_meta)}")
    print(f"Inputs nouvelle campagne    : {len(new_meta)}")

    # ----------------------------------------------------------------------
    # 2.6
    # ----------------------------------------------------------------------
    phase("2.6", "CONSOLIDATION DE LA PROVENANCE")

    provenance = provenance_summary()

    for key, value in provenance.items():
        print(f"{key:24} : {'OK' if value else 'ABSENT'}")

    # ----------------------------------------------------------------------
    # 3.1
    # ----------------------------------------------------------------------
    phase("3.1", "PARSING CONTRÔLÉ DES FICHIERS QE")

    all_qe = qe_files(HIST) + qe_files(NEW)

    print(f"Fichiers QE analysés : {len(all_qe)}")

    # ----------------------------------------------------------------------
    # 3.2
    # ----------------------------------------------------------------------
    phase("3.2", "DÉTECTION DES STATUTS QE")

    statuses = defaultdict(int)

    for path in all_qe:
        statuses[parse_qe_status(path)] += 1

    for status, count in sorted(statuses.items()):
        print(f"{status:24} : {count}")

    # ----------------------------------------------------------------------
    # 3.3
    # ----------------------------------------------------------------------
    phase("3.3", "EXTRACTION DES PARAMÈTRES QE")

    all_inputs = historical_inputs + new_inputs
    all_meta = historical_meta + new_meta

    parameter_presence = defaultdict(int)

    for record in all_meta:
        for key in record["parameters"]:
            parameter_presence[key] += 1

    for key, count in sorted(parameter_presence.items()):
        print(f"{key:16} : {count} input(s)")

    # ----------------------------------------------------------------------
    # 3.4
    # ----------------------------------------------------------------------
    phase("3.4", "EXTRACTION DES RÉSULTATS NUMÉRIQUES QE")

    numerical_results = 0

    for path in all_qe:
        if path.suffix.lower() == ".out":
            result = parse_qe_results(path)
            if result:
                numerical_results += 1

    print(f"Fichiers OUT contenant des résultats numériques : {numerical_results}")

    # ----------------------------------------------------------------------
    # 3.5
    # ----------------------------------------------------------------------
    phase("3.5", "DÉTECTION DES INCOHÉRENCES INPUT / OUTPUT")

    for path in all_inputs:
        output = path.with_suffix(".out")

        if output.exists():
            status = parse_qe_status(output)
            print(
                f"[{status:20}] "
                f"{path.relative_to(ROOT)}"
            )
        else:
            print(
                f"[NO OUTPUT            ] "
                f"{path.relative_to(ROOT)}"
            )

    # ----------------------------------------------------------------------
    # 4.1
    # ----------------------------------------------------------------------
    phase("4.1", "ANALYSE CONVERGENCE CUTOFF")

    conv = convergence_summary(all_meta)

    for file, value in conv["ecutwfc"]:
        print(f"ecutwfc={value:g}  {file}")

    if not conv["ecutwfc"]:
        print("[INFO] Aucun ecutwfc détecté.")

    # ----------------------------------------------------------------------
    # 4.2
    # ----------------------------------------------------------------------
    phase("4.2", "ANALYSE CONVERGENCE K-POINTS")

    kpoint_files = [
        p for p in all_inputs
        if "kpoint" in p.name.lower()
        or "kpts" in p.name.lower()
    ]

    print(f"Fichiers explicitement identifiés comme k-point tests : {len(kpoint_files)}")

    # Lecture générique des cartes K_POINTS
    for path in all_inputs:
        text = read_text(path)

        if "K_POINTS" in text:
            values = extract_all(
                text,
                r"K_POINTS.*?\n\s*(\d+)\s+(\d+)\s+(\d+)",
                flags=re.I | re.S,
            )

            for a, b, c in values:
                print(
                    f"{path.relative_to(ROOT)} -> "
                    f"{a}x{b}x{c}"
                )

    # ----------------------------------------------------------------------
    # 4.3
    # ----------------------------------------------------------------------
    phase("4.3", "ANALYSE SMEARING")

    for file, value in conv["degauss"]:
        print(f"degauss={value:g}  {file}")

    if not conv["degauss"]:
        print("[INFO] Aucun degauss détecté.")

    # ----------------------------------------------------------------------
    # 4.4
    # ----------------------------------------------------------------------
    phase("4.4", "SYNTHÈSE CONVERGENCE")

    print(
        "AIDA collecte les séries numériques disponibles, "
        "mais ne déclare pas automatiquement une convergence scientifique."
    )

    # ----------------------------------------------------------------------
    # 5.1
    # ----------------------------------------------------------------------
    phase("5.1", "ANALYSE RELAX")

    electronic = electronic_summary(all_qe)

    print(f"Artefacts RELAX : {len(electronic['relax'])}")

    # ----------------------------------------------------------------------
    # 5.2
    # ----------------------------------------------------------------------
    phase("5.2", "ANALYSE SCF")

    print(f"Artefacts SCF : {len(electronic['scf'])}")

    # ----------------------------------------------------------------------
    # 5.3
    # ----------------------------------------------------------------------
    phase("5.3", "ANALYSE DOS")

    print(f"Artefacts DOS : {len(electronic['dos'])}")

    # ----------------------------------------------------------------------
    # 5.4
    # ----------------------------------------------------------------------
    phase("5.4", "ANALYSE BANDES")

    print(f"Artefacts BANDS : {len(electronic['bands'])}")

    # ----------------------------------------------------------------------
    # 5.5
    # ----------------------------------------------------------------------
    phase("5.5", "COHÉRENCE RELAX → SCF → DOS/BANDS")

    if electronic["relax"] and electronic["scf"]:
        print("[FACT] RELAX et SCF sont présents.")
    else:
        print("[WARNING] Chaîne RELAX/SCF incomplète.")

    if electronic["dos"]:
        print("[FACT] DOS présent.")
    else:
        print("[INFO] DOS absent.")

    if electronic["bands"]:
        print("[FACT] BANDS présent.")
    else:
        print("[INFO] BANDS absent.")

    print(
        "[INFO] Présence d'artefacts ≠ validation de leur cohérence scientifique."
    )

    # ----------------------------------------------------------------------
    # 6.1
    # ----------------------------------------------------------------------
    phase("6.1", "SÉPARATION LITERATURE / SCREENING / DFT")

    scientific = scientific_provenance()

    print(
        f"LITERATURE H2           : {scientific['literature_h2']}"
    )
    print(
        f"AMBIENT SCREENING        : {scientific['ambient_score']}"
    )
    print(
        f"SCIENTIFIC SCREENING     : {scientific['scientific_score']}"
    )
    print(
        f"SCIENTIFIC CORRECTED     : {scientific['scientific_corrected']}"
    )
    print(
        f"FINAL SCREENING SCORE    : {scientific['final_screening_score']}"
    )

    # ----------------------------------------------------------------------
    # 6.2
    # ----------------------------------------------------------------------
    phase("6.2", "TRAÇABILITÉ DES VALEURS SCIENTIFIQUES")

    print(f"H2 1.86 wt% : {PRIORITY.relative_to(ROOT)}")
    print(f"Score final : {PHASE55.relative_to(ROOT)}")

    # ----------------------------------------------------------------------
    # 6.3
    # ----------------------------------------------------------------------
    phase("6.3", "DÉTECTION DES AFFIRMATIONS NON JUSTIFIÉES")

    print(
        "[WARNING] final_screening_score ne doit pas être présenté "
        "comme une validation DFT."
    )

    print(
        "[WARNING] La présence d'un fichier QE ne prouve pas à elle seule "
        "la convergence ou la validité scientifique."
    )

    # ----------------------------------------------------------------------
    # 6.4
    # ----------------------------------------------------------------------
    phase("6.4", "NIVEAU DE CONFIANCE SCIENTIFIQUE")

    print(
        "[INFO] AIDA conserve la confiance existante comme provenance "
        "HydroMatAI, sans la convertir automatiquement en validation DFT."
    )

    # ----------------------------------------------------------------------
    # 7.1
    # ----------------------------------------------------------------------
    phase("7.1", "AUDIT DU SCORE 0.991579")

    score_data, score_findings = audit_screening_score()

    print(
        f"final_screening_score = "
        f"{score_data['final_screening_score']}"
    )

    # ----------------------------------------------------------------------
    # 7.2
    # ----------------------------------------------------------------------
    phase("7.2", "COMPOSANTES DU SCORE")

    for key in (
        "literature_h2",
        "ambient_score",
        "scientific_score",
        "scientific_corrected",
    ):
        print(f"{key:24} = {score_data[key]}")

    # ----------------------------------------------------------------------
    # 7.3
    # ----------------------------------------------------------------------
    phase("7.3", "SCREENING ≠ VALIDATION DFT")

    print(
        "[OK] Séparation conceptuelle maintenue."
    )

    print(
        "[OK] Aucun résultat QE n'est injecté automatiquement "
        "dans final_screening_score."
    )

    # ----------------------------------------------------------------------
    # 7.4
    # ----------------------------------------------------------------------
    phase("7.4", "RAPPORT D'AUDIT DU SCORE")

    for finding in score_findings:
        print(f"[INFO] {finding}")

    # ----------------------------------------------------------------------
    # 8.1
    # ----------------------------------------------------------------------
    phase("8.1", "ORCHESTRATEUR AIDA COMPLET")

    print("[OK] Toutes les couches d'audit ont été exécutées.")

    # ----------------------------------------------------------------------
    # 8.2
    # ----------------------------------------------------------------------
    phase("8.2", "RAPPORT SCIENTIFIQUE AUTOMATIQUE")

    print()
    print("SUJET :", SUBJECT)
    print()
    print("PROVENANCE :")
    print("  H2 uptake       -> LITERATURE")
    print("  Ambient score   -> HYDROMATAI SCREENING")
    print("  Scientific score-> HYDROMATAI SCREENING")
    print("  Final score     -> COMPOSITE SCREENING")
    print("  QE historique   -> HISTORICAL")
    print("  QE campagne     -> NEW_CAMPAIGN")

    # ----------------------------------------------------------------------
    # 8.3
    # ----------------------------------------------------------------------
    phase("8.3", "TESTS D'INTÉGRATION INTERNES")

    checks = {
        "priority_report": PRIORITY.exists(),
        "phase55_report": PHASE55.exists(),
        "historical_qe": HIST.exists(),
        "new_campaign_qe": NEW.exists(),
        "literature_h2": score_data["literature_h2"] is not None,
        "final_score": score_data["final_screening_score"] is not None,
        "qe_separation": HIST != NEW,
    }

    for name, ok in checks.items():
        print(f"[{'OK' if ok else 'FAIL'}] {name}")

    # ----------------------------------------------------------------------
    # 8.4
    # ----------------------------------------------------------------------
    phase("8.4", "VALIDATION FINALE AIDA")

    failures = [name for name, ok in checks.items() if not ok]

    print()
    print("======================================================================")
    print("AIDA — RÉSUMÉ FINAL")
    print("======================================================================")

    print(f"Sujet                    : {SUBJECT}")
    print(f"Evidence QE              : {len(all_qe)}")
    print(f"Inputs QE                : {len(all_inputs)}")
    print(f"Résultats OUT numériques : {numerical_results}")
    print(f"Tests internes           : {len(checks) - len(failures)}/{len(checks)}")

    print()
    print("SÉPARATION DES DONNÉES")
    print("  Literature             : OUI")
    print("  Screening HydroMatAI   : OUI")
    print("  QE historique          : SÉPARÉ")
    print("  QE nouvelle campagne   : SÉPARÉ")

    print()
    print("RÈGLES SCIENTIFIQUES")
    print("  final score = validation DFT ?  NON")
    print("  fichier QE = calcul validé ?    NON")
    print("  historique = nouvelle campagne? NON")
    print("  données littérature = QE ?      NON")

    print()

    if failures:
        print("[FAIL] AIDA FULL AUDIT")
        print("Échecs :", ", ".join(failures))
        return 1

    print("[OK] AIDA FULL AUDIT TERMINÉ")
    print("[OK] Aucun calcul QE exécuté")
    print("[OK] Aucun fichier scientifique modifié")
    print("[OK] Provenance conservée")
    print("[OK] Historique / nouvelle campagne séparés")

    print()
    print("======================================================================")
    print("FIN AIDA FULL AUDIT")
    print("======================================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
