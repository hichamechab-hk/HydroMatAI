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

    Paramètres principaux :
        calculation : type de calcul QE ('scf', 'relax', 'vc-relax', ...)
        prefix      : préfixe Quantum ESPRESSO
        pseudo_dir  : répertoire des pseudopotentiels
        ecutwfc     : cutoff des fonctions d'onde en Ry
        ecutrho     : cutoff de la densité électronique en Ry
        k_points    : grille k-points (kx, ky, kz)
        smearing    : active le smearing pour les systèmes métalliques
        degauss     : largeur du smearing en Ry
    """

    def __init__(
        self,
        calculation: str = "scf",
        prefix: str = "hydromatai",
        pseudo_dir: str = "/usr/share/espresso/pseudo/",
        ecutwfc: float = 50.0,
        ecutrho: float = 400.0,
        k_points: tuple[int, int, int] = (12, 12, 1),
        smearing: bool = True,
        degauss: float = 0.02,
        nosym: bool = True,
    ):
        self.calculation = calculation
        self.prefix = prefix
        self.pseudo_dir = pseudo_dir

        self.ecutwfc = ecutwfc
        self.ecutrho = ecutrho

        self.k_points = k_points

        self.smearing = smearing
        self.degauss = degauss
        self.nosym = nosym

    def write(self, structure, workdir: Path, material_name: str = "Unknown") -> Path:
        """
        Génère un fichier d'entrée Quantum ESPRESSO.
        """

        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        atoms = structure.atoms

        if not atoms:
            raise ValueError(
                "La structure ne contient aucun atome."
            )

        # ========================================================
        # Déterminer les espèces atomiques
        # ========================================================

        symbols = []

        for atom in atoms:
            if atom.symbol not in symbols:
                symbols.append(atom.symbol)

        # ========================================================
        # Vérifier masses et pseudopotentiels
        # ========================================================

        for symbol in symbols:

            if symbol not in ATOMIC_MASSES:
                raise ValueError(
                    f"Masse atomique inconnue pour l'élément {symbol}."
                )

            if symbol not in PSEUDOPOTENTIALS:
                raise ValueError(
                    f"Pseudopotentiel absent pour l'élément {symbol}."
                )

        # ========================================================
        # ATOMIC_SPECIES
        # ========================================================

        atomic_species = "\n".join(
            f"{symbol} "
            f"{ATOMIC_MASSES[symbol]:.3f} "
            f"{PSEUDOPOTENTIALS[symbol]}"
            for symbol in symbols
        )

        # ========================================================
        # ATOMIC_POSITIONS
        # ========================================================

        atomic_positions = "\n".join(
            f"{atom.symbol} "
            f"{atom.x:.8f} "
            f"{atom.y:.8f} "
            f"{atom.z:.8f}"
            for atom in atoms
        )

        # ========================================================
        # CELL_PARAMETERS
        # ========================================================

        cell = getattr(
    structure,
    "cell",
    [
        [10.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
    ],
    )

        if len(cell) != 3:
            raise ValueError(
                "La cellule doit contenir exactement 3 vecteurs."
            )

        cell_parameters = "\n".join(
            f"{vector[0]:.8f} "
            f"{vector[1]:.8f} "
            f"{vector[2]:.8f}"
            for vector in cell
        )

        # ========================================================
        # K_POINTS
        # ========================================================

        kx, ky, kz = self.k_points

        k_points_block = (
            "K_POINTS automatic\n"
            f"{kx} {ky} {kz} 0 0 0"
        )

        # ========================================================
        # SMearing
        # ========================================================

        smearing_block = ""

        if self.smearing:
            smearing_block = (
                "    occupations = 'smearing',\n"
                "    smearing = 'mv',\n"
                f"    degauss = {self.degauss:.6f},\n"
            )

        # ========================================================
        # BLOCS SPÉCIFIQUES RELAX / VC-RELAX
        # ========================================================

        ions_block = ""

        if self.calculation in {"relax", "vc-relax"}:
            ions_block = "&IONS\n/\n"

        cell_block = ""

        if self.calculation == "vc-relax":
            cell_block = "&CELL\n/\n"

        # ========================================================
        # Fichier QE complet
        # ========================================================

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
    ecutwfc = {self.ecutwfc:.1f},
    ecutrho = {self.ecutrho:.1f},
{smearing_block}{'    nosym = .true.,\n' if self.nosym else ''}/

&ELECTRONS
    conv_thr = 1.0d-8,
    mixing_beta = 0.7,
/

{ions_block}{cell_block}

ATOMIC_SPECIES
{atomic_species}

ATOMIC_POSITIONS angstrom
{atomic_positions}

CELL_PARAMETERS angstrom
{cell_parameters}

{k_points_block}
"""

        # ========================================================
        # Écriture
        # ========================================================

        # Le nom du fichier suit le type de calcul QE.
        # Exemple :
        #   scf     -> scf.in
        #   relax   -> relax.in
        #   vc-relax -> vc-relax.in
        input_file = workdir / f"{self.calculation}.in"

        input_file.write_text(
            content.strip() + "\n",
            encoding="utf-8",
        )

        return input_file
