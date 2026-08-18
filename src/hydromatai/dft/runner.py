from pathlib import Path
import subprocess


class DFTRunner:
    """Exécute un programme DFT externe."""

    def __init__(self, command):
        self.command = command

    def run(self, working_directory: Path):
        result = subprocess.run(
            self.command,
            cwd=working_directory,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout
