from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.structure import CrystalStructure
from hydromatai.core.material import Material

from hydromatai.dft.runner import DFTRunner
from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator


# ============================================================
# 1. Structure H2
# ============================================================

structure = CrystalStructure(
    name="H2",
    cell=[
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
    ],
)

# Distance H-H = 0.8 Å pour le test
structure.add_atom(
    Atom("H", 4.6, 5.0, 5.0)
)

structure.add_atom(
    Atom("H", 5.4, 5.0, 5.0)
)


# ============================================================
# 2. Matériau
# ============================================================

material = Material(
    name="Hydrogen molecule",
    formula="H2",
    structure=structure,
)


# ============================================================
# 3. Runner Quantum ESPRESSO
# ============================================================

workdir = Path("calculations/h2_scf")

QE_COMMAND = "/home/hk/software/quantum-espresso/bin/pw.x"

runner = DFTRunner(
    command=[
        QE_COMMAND,
        "-in",
        "scf.in",
    ]
)

# ============================================================
# 4. Calculateur
# ============================================================

calculator = QuantumEspressoCalculator(
    runner=runner,
    workdir=workdir,
)


# ============================================================
# 5. Génération du fichier d'entrée
# ============================================================

input_file = calculator.prepare_input(material)

print(f"Input QE créé : {input_file}")


# ============================================================
# 6. Exécution de Quantum ESPRESSO
# ============================================================

print("Lancement de Quantum ESPRESSO...")

calculator.run()

print("Calcul QE terminé.")


# ============================================================
# 7. Analyse
# ============================================================

result = calculator.parse_output()


print()
print("========================================")
print("       RESULTAT DFT HYDROMATAI")
print("========================================")
print(f"Calcul réussi : {result.success}")
print(f"Énergie totale : {result.total_energy} Ry")
print("========================================")
