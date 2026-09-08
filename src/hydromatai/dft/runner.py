from pathlib import Path
import subprocess


class DFTRunner:
    """Exécute un programme DFT externe."""

    def __init__(self, command):
        self.command = command

    def run(self, working_directory: Path):
        working_directory = Path(working_directory)
        working_directory.mkdir(parents=True, exist_ok=True)

        command = list(self.command)

        # --------------------------------------------------------
        # Normaliser le fichier d'entrée QE
        # --------------------------------------------------------
        # Exemple :
        #   pw.x -in relax.in
        #
        # devient :
        #   pw.x -in /tmp/.../relax.in
        #
        # Cela évite les problèmes de résolution du chemin lorsque
        # le runner est appelé depuis un workflow.
        # --------------------------------------------------------

        for i, argument in enumerate(command):
            if argument == "-in" and i + 1 < len(command):
                input_file = Path(command[i + 1])

                if not input_file.is_absolute():
                    command[i + 1] = str(
                        working_directory / input_file
                    )

        result = subprocess.run(
            command,
            cwd=working_directory,
            capture_output=True,
            text=True,
            check=True,
        )

        # ----------------------------------------------------
        # Sauvegarder systématiquement stdout QE.
        #
        # Le nom est déduit de l'argument fourni après -in :
        #
        #   -in relax.in -> relax.out
        #   -in scf.in   -> scf.out
        #
        # stdout reste également retourné afin de préserver
        # l'API historique de DFTRunner.
        # ----------------------------------------------------

        output_file = None

        for i, argument in enumerate(command):
            if argument == "-in" and i + 1 < len(command):
                input_path = Path(command[i + 1])

                output_file = (
                    working_directory
                    / input_path.with_suffix(".out").name
                )

                break

        if output_file is None:
            output_file = (
                working_directory
                / "dft.out"
            )

        output_file.write_text(
            result.stdout,
            encoding="utf-8",
        )

        return result.stdout
