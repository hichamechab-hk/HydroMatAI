from __future__ import annotations
"""Automatic electronic-property plots."""


from pathlib import Path


def plot_dos(
    energy,
    dos,
    output: str | Path,
    fermi_energy: float = 0.0,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(energy, dos)
    plt.axvline(
        fermi_energy,
        linestyle="--",
        label="Fermi level",
    )

    plt.xlabel("Energy (eV)")
    plt.ylabel("DOS")
    plt.title("Density of States")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()


def plot_bands(
    kpoints,
    bands,
    output: str | Path,
    fermi_energy: float = 0.0,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))

    for band in bands:
        plt.plot(kpoints, band)

    plt.axhline(
        fermi_energy,
        linestyle="--",
        label="Fermi level",
    )

    plt.xlabel("k-path")
    plt.ylabel("Energy (eV)")
    plt.title("Electronic Band Structure")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()
