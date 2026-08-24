import re

from hydromatai.core.atom import Atom
from hydromatai.core.structure import CrystalStructure
from hydromatai.dft.output import DFTResult
from hydromatai.dft.exceptions import DFTParseError


class QEParser:
    """
    Analyse la sortie texte de Quantum ESPRESSO pw.x.

    Extrait :
        - énergie totale
        - géométrie finale
        - cellule finale
        - forces éventuelles
        - structure relaxée
    """

    ENERGY_PATTERN = re.compile(
        r"!\s+total energy\s+=\s+"
        r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry"
    )

    FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"

    POSITION_LINE_PATTERN = re.compile(
        rf"^\s*([A-Za-z][A-Za-z]?)\s+"
        rf"({FLOAT})\s+"
        rf"({FLOAT})\s+"
        rf"({FLOAT})"
    )

    CELL_LINE_PATTERN = re.compile(
        rf"^\s*({FLOAT})\s+"
        rf"({FLOAT})\s+"
        rf"({FLOAT})\s*$"
    )

    FORCE_PATTERN = re.compile(
        rf"force\s+=\s+\(\s*"
        rf"({FLOAT})\s+"
        rf"({FLOAT})\s+"
        rf"({FLOAT})\s*\)"
    )

    def _to_float(self, value: str) -> float:
        """
        Convertit un nombre QE en float.

        Supporte également la notation scientifique
        Fortran D/d.
        """

        return float(
            value.replace("D", "E").replace("d", "e")
        )

    # ============================================================
    # ELECTRONIC LEVELS
    # ============================================================

    def _parse_electronic_levels(self, raw_output: str):
        """
        Extrait VBM, CBM et énergie de Fermi depuis une sortie QE.
        """

        pattern = re.compile(
            r"highest occupied, lowest unoccupied level\s*"
            r"\(ev\):\s*"
            r"([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)\s+"
            r"([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)",
            re.IGNORECASE,
        )

        match = pattern.search(raw_output)

        if match:
            vbm = self._to_float(match.group(1))
            cbm = self._to_float(match.group(2))
            return vbm, cbm, None

        fermi_pattern = re.compile(
            r"the Fermi energy is\s+"
            r"([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)\s+ev",
            re.IGNORECASE,
        )

        match = fermi_pattern.search(raw_output)

        if match:
            fermi = self._to_float(match.group(1))
            return None, None, fermi

        return None, None, None

    # ============================================================
    # ATOMIC POSITIONS
    # ============================================================

    def _parse_positions(self, raw_output: str):
        """
        Extrait la dernière section ATOMIC_POSITIONS.

        Retourne :
            list[Atom] ou None
        """

        lines = raw_output.splitlines()

        sections = []

        for i, line in enumerate(lines):

            if line.strip().upper().startswith(
                "ATOMIC_POSITIONS"
            ):

                atoms = []

                j = i + 1

                while j < len(lines):

                    match = self.POSITION_LINE_PATTERN.match(
                        lines[j]
                    )

                    if not match:
                        break

                    symbol = match.group(1)

                    x = self._to_float(match.group(2))
                    y = self._to_float(match.group(3))
                    z = self._to_float(match.group(4))

                    atoms.append(
                        Atom(
                            symbol=symbol,
                            x=x,
                            y=y,
                            z=z,
                        )
                    )

                    j += 1

                if atoms:
                    sections.append(atoms)

        if not sections:
            return None

        # La dernière section correspond à la géométrie finale
        return sections[-1]

    # ============================================================
    # CELL PARAMETERS
    # ============================================================

    def _parse_cell(self, raw_output: str):
        """
        Extrait la dernière section CELL_PARAMETERS.

        Retourne :
            list[list[float]] ou None
        """

        lines = raw_output.splitlines()

        sections = []

        for i, line in enumerate(lines):

            if line.strip().upper().startswith(
                "CELL_PARAMETERS"
            ):

                cell = []

                for j in range(
                    i + 1,
                    min(i + 4, len(lines)),
                ):

                    match = self.CELL_LINE_PATTERN.match(
                        lines[j]
                    )

                    if not match:
                        break

                    cell.append(
                        [
                            self._to_float(match.group(1)),
                            self._to_float(match.group(2)),
                            self._to_float(match.group(3)),
                        ]
                    )

                if len(cell) == 3:
                    sections.append(cell)

        if not sections:
            return None

        # Dernière cellule = cellule finale
        return sections[-1]

    # ============================================================
    # FORCES
    # ============================================================

    def _parse_forces(self, raw_output: str):
        """
        Extrait les forces atomiques présentes dans la sortie QE.

        Retourne les dernières forces trouvées.
        """

        lines = raw_output.splitlines()

        force_sections = []

        current = []

        for line in lines:

            match = self.FORCE_PATTERN.search(line)

            if match:

                current.append(
                    [
                        self._to_float(match.group(1)),
                        self._to_float(match.group(2)),
                        self._to_float(match.group(3)),
                    ]
                )

            elif current and (
                "Total force" in line
                or "Total SCF correction" in line
            ):

                force_sections.append(current)
                current = []

        if current:
            force_sections.append(current)

        if not force_sections:
            return None

        return force_sections[-1]

    # ============================================================
    # CONSTRUCTION STRUCTURE RELAXÉE
    # ============================================================

    def _build_relaxed_structure(
        self,
        atoms,
        cell,
    ):
        """
        Construit une CrystalStructure à partir de la géométrie
        finale extraite de Quantum ESPRESSO.
        """

        if atoms is None:
            return None

        relaxed_structure = CrystalStructure(
            name="QE_relaxed",
            atoms=atoms,
        )

        if cell is not None:
            relaxed_structure.cell = cell

        return relaxed_structure

    # ============================================================
    # PARSER PRINCIPAL
    # ============================================================

    def parse(self, raw_output: str) -> DFTResult:
        """
        Analyse complètement une sortie Quantum ESPRESSO.
        """

        if not raw_output:
            raise DFTParseError(
                "La sortie Quantum ESPRESSO est vide."
            )

        # --------------------------------------------------------
        # 1. ÉNERGIE TOTALE
        # --------------------------------------------------------

        matches = self.ENERGY_PATTERN.findall(
            raw_output
        )

        if not matches:
            raise DFTParseError(
                "Impossible de trouver l'énergie totale "
                "dans la sortie QE."
            )

        # Dernière énergie = énergie finale
        total_energy = float(
            matches[-1]
        )

        # --------------------------------------------------------
        # 2. POSITIONS FINALES
        # --------------------------------------------------------

        atoms = self._parse_positions(
            raw_output
        )

        # --------------------------------------------------------
        # 3. CELLULE FINALE
        # --------------------------------------------------------

        cell = self._parse_cell(
            raw_output
        )

        # --------------------------------------------------------
        # 4. FORCES FINALES
        # --------------------------------------------------------

        forces = self._parse_forces(
            raw_output
        )

        # --------------------------------------------------------
        # 5. CONSTRUIRE LA STRUCTURE RELAXÉE
        # --------------------------------------------------------

        relaxed_structure = (
            self._build_relaxed_structure(
                atoms=atoms,
                cell=cell,
            )
        )

        # --------------------------------------------------------
        # 5b. NIVEAUX ÉLECTRONIQUES
        # --------------------------------------------------------

        vbm, cbm, fermi_energy = self._parse_electronic_levels(
            raw_output
        )

        band_gap = None

        if vbm is not None and cbm is not None:
            band_gap = max(0.0, cbm - vbm)

        # --------------------------------------------------------
        # 6. RÉSULTAT DFT
        # --------------------------------------------------------

        return DFTResult(
            success=True,
            total_energy=total_energy,
            band_gap=band_gap,
            vbm=vbm,
            cbm=cbm,
            fermi_energy=fermi_energy,
            forces=forces,

            # IMPORTANT :
            # la structure finale du RELAX est maintenant
            # retournée dans DFTResult.
            relaxed_structure=relaxed_structure,

            raw_output=raw_output,
        )
