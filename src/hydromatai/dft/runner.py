from pathlib import Path
import subprocess

from .exceptions import DFTRunError


class DFTRunner:
    """
    Exécute une commande DFT dans un répertoire de travail.
    """

    def __init__(self, command: list[str]):
        self.command = command

    def run(self, workdir: str | Path) -> str:
        workdir = Path(workdir)

        if not workdir.exists():
            raise DFTRunError(
                f"Répertoire inexistant: {workdir}"
            )

        try:
            result = subprocess.run(
                self.command,
                cwd=workdir,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise DFTRunError(
                f"Le calcul DFT a échoué: {exc}"
            ) from exc

        return result.stdout
