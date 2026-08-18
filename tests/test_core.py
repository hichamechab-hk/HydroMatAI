from hydromatai.core.atom import Atom
from hydromatai.core.structure import CrystalStructure


def test_structure():

    atom = Atom(
        symbol="H",
        x=0,
        y=0,
        z=0
    )

    crystal = CrystalStructure(
        name="Test"
    )

    crystal.add_atom(atom)

    assert crystal.number_of_atoms() == 1
