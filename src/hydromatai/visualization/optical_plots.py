from __future__ import annotations
"""Automatic optical-property plots."""


from pathlib import Path


def plot_dielectric(
    energy,
    epsilon_real,
    epsilon_imag,
    output: str | Path,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))

    plt.plot(
        energy,
        epsilon_real,
        label="ε1",
    )

    plt.plot(
        energy,
        epsilon_imag,
        label="ε2",
    )

    plt.xlabel("Photon energy (eV)")
    plt.ylabel("Dielectric function")
    plt.title("Optical Dielectric Function")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()


def plot_reflectivity(
    energy,
    reflectivity,
    output: str | Path,
):
    import matplotlib.pyplot as plt

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(8, 5))
    plt.plot(energy, reflectivity)

    plt.xlabel("Photon energy (eV)")
    plt.ylabel("Reflectivity")
    plt.title("Optical Reflectivity")
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    plt.close()
