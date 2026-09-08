#!/usr/bin/env python3
import os
os.system("clear")
# scripts/phase23_qe_run.py

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PROJECT = Path("/home/hk/HydroMatAI")
QE_ROOT = Path("/home/hk/software/qe-7.5")
PW_X = QE_ROOT / "bin" / "pw.x"

PHASE22_DIR = PROJECT / "calculations" / "phase_22_qe_inputs"
OUT_DIR = PROJECT / "calculations" / "phase_23_qe_runs"

CSV22 = PHASE22_DIR / "phase22_qe_inputs.csv"
JSON22 = PHASE22_DIR / "phase22_qe_inputs.json"
MANIFEST22 = PHASE22_DIR / "phase22_manifest.json"

CSV23 = OUT_DIR / "phase23_qe_runs.csv"
JSON23 = OUT_DIR / "phase23_qe_runs.json"
MANIFEST23 = OUT_DIR / "phase23_manifest.json"


def now():
    return datetime.now().astimezone().isoformat()


def die(msg):
    print(f"ERREUR : {msg}", file=sys.stderr)
    sys.exit(1)


def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def normalize_records(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in (
            "candidates",
            "results",
            "records",
            "qe_inputs",
            "phase22_results",
            "items",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def find_input(record):
    candidates = [
        record.get("input_qe"),
        record.get("qe_input"),
        record.get("input_file"),
        record.get("qe_file"),
        record.get("path"),
    ]

    for value in candidates:
        if value:
            p = Path(str(value))
            if not p.is_absolute():
                p = PROJECT / p
            if p.is_file():
                return p

    name = (
        record.get("name")
        or record.get("candidate")
        or record.get("candidate_name")
        or record.get("id")
    )

    if name:
        p = PHASE22_DIR / str(name) / f"{name}.in"
        if p.is_file():
            return p

    return None


def candidate_name(record, input_path):
    return str(
        record.get("name")
        or record.get("candidate")
        or record.get("candidate_name")
        or record.get("id")
        or input_path.stem
    )


def validate_input(path):
    if not path.is_file():
        return False, "INPUT_NOT_FOUND"

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return False, f"INPUT_READ_ERROR: {exc}"

    required = [
        "&CONTROL",
        "&SYSTEM",
        "&ELECTRONS",
        "ATOMIC_SPECIES",
        "ATOMIC_POSITIONS",
        "K_POINTS",
    ]

    upper = text.upper()

    for token in required:
        if token not in upper:
            return False, f"MISSING_{token.replace('&', '')}"

    if "CELL_PARAMETERS" not in upper:
        # Acceptibrable si ibrav != 0.
        m = re.search(r"\bibrav\s*=\s*([+-]?\d+)", text, re.I)
        if not m or int(m.group(1)) == 0:
            return False, "MISSING_CELL_PARAMETERS"

    return True, "OK"


def detect_status(stdout, returncode):
    text = stdout.upper()

    fatal_patterns = [
        "ERROR",
        "BAD TERMINATION",
        "CANNOT OPEN",
        "NOT FOUND",
        "FORTRAN STOP",
        "SEGMENTATION FAULT",
        "MPI_ABORT",
        "FAILED",
    ]

    if returncode != 0:
        return "FAILED"

    for pattern in fatal_patterns:
        if pattern in text:
            return "FAILED"

    if "JOB DONE." in text:
        return "COMPLETED"

    return "FINISHED_WITHOUT_JOB_DONE"


def run_one(name, input_path, timeout):
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    output_path = run_dir / f"{name}.out"
    log_path = run_dir / "run.log"
    copied_input = run_dir / input_path.name

    if not copied_input.exists():
        shutil.copy2(input_path, copied_input)

    valid, validation = validate_input(copied_input)

    if not valid:
        return {
            "candidate": name,
            "input_qe": str(input_path),
            "run_dir": str(run_dir),
            "output": str(output_path),
            "status": "INPUT_INVALID",
            "validation": validation,
            "returncode": None,
            "started_at": None,
            "finished_at": now(),
            "elapsed_seconds": 0.0,
        }

    started = now()
    t0 = time.monotonic()

    command = [str(PW_X), "-in", copied_input.name]

    try:
        with output_path.open("w", encoding="utf-8") as out:
            proc = subprocess.run(
                command,
                cwd=run_dir,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )

        returncode = proc.returncode

        stdout = output_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        status = detect_status(stdout, returncode)

    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
        returncode = None

    except Exception as exc:
        status = "EXECUTION_ERROR"
        returncode = None
        with output_path.open("a", encoding="utf-8") as out:
            out.write(f"\n\nPHASE23 EXCEPTION: {exc}\n")

    elapsed = time.monotonic() - t0
    finished = now()

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"candidate={name}\n")
        log.write(f"input={copied_input}\n")
        log.write(f"command={' '.join(command)}\n")
        log.write(f"started={started}\n")
        log.write(f"finished={finished}\n")
        log.write(f"elapsed_seconds={elapsed:.3f}\n")
        log.write(f"returncode={returncode}\n")
        log.write(f"status={status}\n")

    return {
        "candidate": name,
        "input_qe": str(input_path),
        "run_dir": str(run_dir),
        "output": str(output_path),
        "status": status,
        "validation": validation,
        "returncode": returncode,
        "started_at": started,
        "finished_at": finished,
        "elapsed_seconds": round(elapsed, 3),
    }


def load_phase22():
    if JSON22.exists():
        return normalize_records(read_json(JSON22))

    if CSV22.exists():
        with CSV22.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    die(
        "Phase 22 introuvable : "
        f"{JSON22} ou {CSV22}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="HydroMatAI Phase 23 — exécution contrôlée de pw.x"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre maximum de candidats",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=7200,
        help="Timeout par calcul en secondes",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Ne pas relancer les calculs déjà COMPLETED",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valider les inputs sans lancer pw.x",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("HydroMatAI — PHASE 23")
    print("EXÉCUTION QUANTUM ESPRESSO")
    print("=" * 80)

    print("\nCONFIGURATION")
    print("-" * 80)
    print(f"Projet       : {PROJECT}")
    print(f"QE           : {QE_ROOT}")
    print(f"pw.x         : {PW_X}")
    print(f"Phase 22     : {PHASE22_DIR}")
    print(f"Sorties      : {OUT_DIR}")

    if not PROJECT.is_dir():
        die(f"Projet absent : {PROJECT}")

    if not PW_X.is_file():
        die(f"pw.x absent : {PW_X}")

    if not os.access(PW_X, os.X_OK):
        die(f"pw.x non exécutable : {PW_X}")

    if not PHASE22_DIR.is_dir():
        die(f"Répertoire Phase 22 absent : {PHASE22_DIR}")

    records = load_phase22()

    if not records:
        die("Aucun candidat trouvé dans les résultats Phase 22.")

    selected = []

    for record in records:
        input_path = find_input(record)

        if input_path is None:
            continue

        name = candidate_name(record, input_path)

        status22 = str(
            record.get("status")
            or record.get("STATUS")
            or record.get("phase22_status")
            or "READY_FOR_QE_INPUT"
        ).upper()

        if "READY_FOR_QE_INPUT" not in status22 and status22 not in (
            "READY",
            "OK",
        ):
            continue

        selected.append(
            {
                "record": record,
                "name": name,
                "input": input_path,
            }
        )

    if args.limit is not None:
        selected = selected[: args.limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nCANDIDATS")
    print("-" * 80)
    print(f"Phase 22 disponibles : {len(records)}")
    print(f"READY_FOR_QE_INPUT    : {len(selected)}")

    if not selected:
        die("Aucun input Phase 22 READY_FOR_QE_INPUT trouvé.")

    print("\nPRÉ-VÉRIFICATION")
    print("-" * 80)

    valid_count = 0

    for item in selected:
        valid, reason = validate_input(item["input"])

        if valid:
            valid_count += 1
            print(f"[OK]   {item['name']} → {item['input']}")
        else:
            print(f"[FAIL] {item['name']} → {reason}")

    if valid_count != len(selected):
        die(
            f"{len(selected) - valid_count} input(s) QE invalide(s). "
            "Aucun calcul ne sera lancé."
        )

    if args.dry_run:
        print("\nDRY-RUN : aucun pw.x lancé.")

        results = []
        for item in selected:
            results.append(
                {
                    "candidate": item["name"],
                    "input_qe": str(item["input"]),
                    "status": "VALIDATED_ONLY",
                }
            )

    else:
        print("\nEXÉCUTION QE")
        print("-" * 80)
        print("pw.x sera lancé candidat par candidat.")
        print("Aucun calcul parallèle.")

        results = []

        for index, item in enumerate(selected, 1):
            name = item["name"]

            previous_out = OUT_DIR / name / f"{name}.out"

            if args.resume and previous_out.exists():
                try:
                    previous_text = previous_out.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                except Exception:
                    previous_text = ""

                if "JOB DONE." in previous_text.upper():
                    print(
                        f"[{index}/{len(selected)}] {name}"
                        " → SKIPPED_ALREADY_COMPLETED"
                    )

                    results.append(
                        {
                            "candidate": name,
                            "input_qe": str(item["input"]),
                            "run_dir": str(OUT_DIR / name),
                            "output": str(previous_out),
                            "status": "SKIPPED_ALREADY_COMPLETED",
                            "validation": "OK",
                            "returncode": 0,
                            "started_at": None,
                            "finished_at": now(),
                            "elapsed_seconds": 0.0,
                        }
                    )
                    continue

            print(f"\n[{index}/{len(selected)}] {name}")
            print(f"  Input : {item['input']}")
            print("  pw.x  : LANCÉ")

            result = run_one(
                name=name,
                input_path=item["input"],
                timeout=args.timeout,
            )

            results.append(result)

            print(f"  STATUS : {result['status']}")
            print(f"  Output : {result['output']}")

    completed = sum(
        r["status"] in ("COMPLETED", "SKIPPED_ALREADY_COMPLETED")
        for r in results
    )
    failed = len(results) - completed

    # CSV
    fields = [
        "candidate",
        "input_qe",
        "run_dir",
        "output",
        "status",
        "validation",
        "returncode",
        "started_at",
        "finished_at",
        "elapsed_seconds",
    ]

    with CSV23.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(results)

    write_json(
        JSON23,
        {
            "phase": 23,
            "generated_at": now(),
            "project": str(PROJECT),
            "qe_root": str(QE_ROOT),
            "pw_x": str(PW_X),
            "phase22_source": str(JSON22 if JSON22.exists() else CSV22),
            "dry_run": args.dry_run,
            "resume": args.resume,
            "timeout_seconds": args.timeout,
            "candidates": results,
            "summary": {
                "selected": len(selected),
                "completed": completed,
                "failed": failed,
            },
        },
    )

    write_json(
        MANIFEST23,
        {
            "phase": 23,
            "created_at": now(),
            "status": "COMPLETED" if failed == 0 else "PARTIAL",
            "pw_x": str(PW_X),
            "output_directory": str(OUT_DIR),
            "csv": str(CSV23),
            "json": str(JSON23),
            "candidates": [
                {
                    "candidate": r["candidate"],
                    "status": r["status"],
                    "output": r.get("output"),
                }
                for r in results
            ],
        },
    )

    print("\n" + "=" * 80)
    print("PHASE 23 — RÉSULTATS")
    print("=" * 80)
    print(f"Candidats sélectionnés : {len(selected)}")
    print(f"Calculs terminés       : {completed}")
    print(f"Échecs                 : {failed}")

    print("\n" + "-" * 80)
    print("FICHIERS")
    print("-" * 80)
    print(f"CSV      : {CSV23}")
    print(f"JSON     : {JSON23}")
    print(f"MANIFEST : {MANIFEST23}")

    print("\n" + "=" * 80)
    print("PHASE 23 — AUDIT FINAL")
    print("=" * 80)
    print("Lecture Phase 22       : OK")
    print("Validation inputs QE   : OK")
    print(f"pw.x lancé              : {'NON' if args.dry_run else 'OUI'}")
    print(f"Calcul QE lancé         : {'NON' if args.dry_run else 'OUI'}")
    print("Aucun CIF modifié       : OK")
    print("Traçabilité             : OK")

    if args.dry_run:
        print("\nREADY_FOR_QE_RUN : OUI")
        print("MODE : DRY-RUN")
    elif failed == 0:
        print("\nREADY_FOR_QE_RUN : OUI")
        print("BLOCAGE             : AUCUN")
    else:
        print("\nREADY_FOR_QE_RUN : PARTIEL")
        print(f"BLOCAGE             : {failed} calcul(s)")

    print("=" * 80)
    print("PHASE 23 — TERMINÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
