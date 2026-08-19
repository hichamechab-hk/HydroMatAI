from hydromatai.dft.quantum_espresso.input_generator import QEInputGenerator


class FakeAtom:

    def __init__(self, symbol, x, y, z):
        self.symbol = symbol
        self.x = x
        self.y = y
        self.z = z



class FakeStructure:

    def __init__(self):
        self.atoms = [
            FakeAtom("C",0,0,0),
            FakeAtom("C",1.42,0,0),
        ]



def test_qe_input_generation(tmp_path):

    structure = FakeStructure()

    generator = QEInputGenerator()

    path = generator.write(
        structure,
        tmp_path
    )

    assert path.exists()

    content = path.read_text()

    assert "ATOMIC_SPECIES" in content
    assert "ATOMIC_POSITIONS" in content
    assert "C.pbe-n-kjpaw_psl.0.1.UPF" in content
