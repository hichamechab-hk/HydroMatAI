from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
QE_ROOT = ROOT / "calculations/global_screening/qe/TOP20"

OLD = "C.UPF"
NEW = "C.pbe-n-kjpaw_psl.0.1.UPF"

changed = 0

for path in sorted(QE_ROOT.glob("*/pw.scf.in")):
    text = path.read_text(encoding="utf-8")

    if OLD in text:
        path.write_text(text.replace(OLD, NEW), encoding="utf-8")
        changed += 1
        print(f"[OK] Corrigé : {path}")

print()
print(f"Inputs corrigés : {changed}/20")

if changed == 0:
    print("[INFO] Aucun C.UPF trouvé — rien à modifier.")
elif changed > 20:
    raise SystemExit("[ERROR] Nombre inattendu d'inputs corrigés.")

print("[OK] Correction terminée.")
