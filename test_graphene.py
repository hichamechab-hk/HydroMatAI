from pathlib import Path

from hydromatai.core.atom import Atom
from hydromatai.core.material import Material
from hydromatai.core.structure import CrystalStructure
from hydromatai.dft.quantum_espresso import QuantumEspressoCalculator


# ============================================================
# 1. Paramètres du graphène
# ============================================================

# Paramètre de maille du graphène en Å
a = 2.46

# Grande séparation entre les couches de graphène
# pour éviter les interactions périodiques selon z
vacuum = 20.0


# ============================================================
# 2. Construction de la cellule primitive
# ============================================================

structure = CrystalStructure(
    name="Graphene",
    cell=[
        [a, 0.0, 0.0],
        [a / 2.0, a * (3.0 ** 0.5) / 2.0, 0.0],
        [0.0, 0.0, vacuum],
    ],
)


# ============================================================
# 3. Deux atomes de carbone dans la cellule primitive
# ============================================================

structure.add_atom(
    Atom(
        symbol="C",
        x=0.0,
        y=0.0,
        z=0.0,
    )
)

structure.add_atom(
    Atom(
        symbol="C",
        x=a / 2.0,
        y=a * (3.0 ** 0.5) / 6.0,
        z=0.0,
    )
)


# ============================================================
# 4. Création du matériau
# ============================================================

graphene = Material(
    name="Graphene",
    formula="C2",
    structure=structure,
)


# ============================================================
# 5. Affichage de contrôle
# ============================================================

print("=" * 60)
print("        STRUCTURE DU GRAPHÈNE")
print("=" * 60)

print(f"Nom       : {graphene.name}")
print(f"Formule   : {graphene.formula}")
print(f"Atomes    : {structure.number_of_atoms()}")

print("\nCellule (Å):")

for vector in structure.cell:
    print(
        f"  {vector[0]:12.6f}"
        f" {vector[1]:12.6f}"
        f" {vector[2]:12.6f}"
    )

print("\nPositions atomiques (Å):")

for atom in structure.atoms:
    print(
        f"  {atom.symbol:2s}"
        f" {atom.x:12.6f}"
        f" {atom.y:12.6f}"
        f" {atom.z:12.6f}"
    )


# ============================================================
# 6. Génération du fichier Quantum ESPRESSO
# ============================================================

workdir = Path("calculations/graphene_scf")

calculator = QuantumEspressoCalculator(
    runner=None,
    workdir=workdir,
)

input_file = calculator.prepare_input(graphene)


# ============================================================
# 7. Résultat
# ============================================================

print("\n" + "=" * 60)
print("        FICHIER QE GÉNÉRÉ")
print("=" * 60)

print(f"Fichier : {input_file}")

print("\nContenu de scf.in :")
print("-" * 60)
print(input_file.read_text())
print("-" * 60)
