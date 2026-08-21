from pathlib import Path


ATOMIC_MASSES = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "Al": 26.982,
    "Ti": 47.867,
}


PSEUDOPOTENTIALS = {
    "H": "H.pbe-kjpaw.UPF",
    "C": "C.pbe-n-kjpaw_psl.0.1.UPF",
    "N": "N.pbe-n-kjpaw_psl.0.1.UPF",
    "O": "O.pbe-kjpaw_psl.0.1.UPF",
    "Al": "Al.pz-vbc.UPF",
    "Ti": "Ti.pz-sp-van_ak.UPF",
}


class QEInputGenerator:
    """
    Générateur de fichiers d'entrée Quantum ESPRESSO.
    """

    def __init__(
        self,
        calculation: str = "scf",
        prefix: str = "hydromatai",
        pseudo_dir: str = "/usr/share/espresso/pseudo/",
    ):
        self.calculation = calculation
        self.prefix = prefix
        self.pseudo_dir = pseudo_dir

    def write(self, structure, workdir: Path) -> Path:
        """
        Génère un fichier scf.in Quantum ESPRESSO.
        """

        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        atoms = structure.atoms

        if not atoms:
            raise ValueError(
                "La structure ne contient aucun atome."
            )

        # --------------------------------------------------------
        # Éléments présents dans la structure
        # --------------------------------------------------------

        symbols = []

        for atom in atoms:
            if atom.symbol not in symbols:
                symbols.append(atom.symbol)

        # --------------------------------------------------------
        # Vérification des masses et pseudopotentiels
        # --------------------------------------------------------

        for symbol in symbols:

            if symbol not in ATOMIC_MASSES:
                raise ValueError(
                    f"Masse atomique inconnue pour l'élément {symbol}."
                )

            if symbol not in PSEUDOPOTENTIALS:
                raise ValueError(
                    f"Pseudopotentiel absent pour l'élément {symbol}."
                )

        # --------------------------------------------------------
        # ATOMIC_SPECIES
        # --------------------------------------------------------

        atomic_species = "\n".join(
            f"{symbol} "
            f"{ATOMIC_MASSES[symbol]:.3f} "
            f"{PSEUDOPOTENTIALS[symbol]}"
            for symbol in symbols
        )

        # --------------------------------------------------------
        # ATOMIC_POSITIONS
        # --------------------------------------------------------

        atomic_positions = "\n".join(
            f"{atom.symbol} "
            f"{atom.x:.8f} "
            f"{atom.y:.8f} "
            f"{atom.z:.8f}"
            for atom in atoms
        )

        # --------------------------------------------------------
        # CELL_PARAMETERS
        # --------------------------------------------------------

        cell = getattr(
            structure,
            "cell",
            [
                [10.0, 0.0, 0.0],
                [0.0, 10.0, 0.0],
                [0.0, 0.0, 10.0],
            ],
        )

        cell_parameters = "\n".join(
            f"{vector[0]:.8f} "
            f"{vector[1]:.8f} "
            f"{vector[2]:.8f}"
            for vector in cell
        )

        # --------------------------------------------------------
        # Nom du matériau
        # --------------------------------------------------------

        material_name = getattr(
            structure,
            "name",
            "Unknown",
        )

        # --------------------------------------------------------
        # Fichier d'entrée Quantum ESPRESSO
        # --------------------------------------------------------

        content = f"""! HydroMatAI Quantum ESPRESSO input
! Material: {material_name}

&CONTROL
    calculation = '{self.calculation}',
    prefix = '{self.prefix}',
    pseudo_dir = '{self.pseudo_dir}',
/

&SYSTEM
    ibrav = 0,
    nat = {len(atoms)},
    ntyp = {len(symbols)},
    ecutwfc = 50.0,
    ecutrho = 400.0,
/

&ELECTRONS
    conv_thr = 1.0d-8,
    mixing_beta = 0.7,
/

ATOMIC_SPECIES
{atomic_species}

ATOMIC_POSITIONS angstrom
{atomic_positions}

CELL_PARAMETERS angstrom
{cell_parameters}

K_POINTS automatic
1 1 1 0 0 0
"""

        # --------------------------------------------------------
        # Écriture du fichier
        # --------------------------------------------------------

        input_file = workdir / "scf.in"

        input_file.write_text(
            content.strip() + "\n"
        )

        return input_file
