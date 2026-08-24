from pathlib import Path

from hydromatai.properties.electronic.dos import (
    DOSData,
    read_fermi_energy,
    parse_dos_file,
    find_band_gap,
)

from hydromatai.properties.electronic.bands import (
    BandData,
    read_band_data,
    estimate_band_gap,
)

from hydromatai.properties.electronic.analyzer import (
    ElectronicInterpretation,
    interpret_band_gap,
)


# ============================================================
# DOS
# ============================================================


def test_dos_data():

    data = DOSData(
        energy=[-1.0, 0.0, 1.0],
        values=[2.0, 0.0, 3.0],
        fermi_energy=0.0,
    )

    assert data.energy == [-1.0, 0.0, 1.0]
    assert data.values == [2.0, 0.0, 3.0]
    assert data.fermi_energy == 0.0


def test_read_fermi_energy():

    text = """
    some QE output
    the Fermi energy is    5.4321 ev
    """

    fermi = read_fermi_energy(text)

    assert fermi == 5.4321


def test_read_fermi_energy_fortran_notation():

    text = """
    highest occupied level    3.25D+00 eV
    """

    fermi = read_fermi_energy(text)

    assert fermi == 3.25


def test_parse_dos_file(tmp_path: Path):

    dos_file = tmp_path / "dos.dat"

    dos_file.write_text(
        """
# Energy DOS
-2.0  0.0
-1.0  2.0
 0.0  0.0
 1.0  0.0
 2.0  3.0
invalid line
""",
        encoding="utf-8",
    )

    data = parse_dos_file(dos_file)

    assert data.energy == [
        -2.0,
        -1.0,
        0.0,
        1.0,
        2.0,
    ]

    assert data.values == [
        0.0,
        2.0,
        0.0,
        0.0,
        3.0,
    ]


def test_find_dos_band_gap():

    energy = [
        -2.0,
        -1.0,
        -0.5,
        0.0,
        0.5,
        1.0,
        2.0,
    ]

    dos = [
        0.0,
        1.0,
        2.0,
        0.0,
        0.0,
        3.0,
        4.0,
    ]

    gap = find_band_gap(
        energy,
        dos,
    )

    assert gap == 1.5


def test_find_dos_band_gap_empty():

    gap = find_band_gap(
        [],
        [],
    )

    assert gap is None


# ============================================================
# BANDS
# ============================================================


def test_band_data():

    data = BandData(
        kpoints=[0.0, 0.5, 1.0],
        bands=[
            [-2.0, -1.5, -1.0],
            [1.0, 1.5, 2.0],
        ],
        fermi_energy=0.0,
    )

    assert data.kpoints == [
        0.0,
        0.5,
        1.0,
    ]

    assert len(data.bands) == 2


def test_read_band_data(tmp_path: Path):

    band_file = tmp_path / "bands.dat"

    band_file.write_text(
        """
# k band1 band2
0.0 -2.0 1.0
0.5 -1.5 1.5
1.0 -1.0 2.0
invalid
""",
        encoding="utf-8",
    )

    data = read_band_data(
        band_file
    )

    assert data.kpoints == [
        0.0,
        0.5,
        1.0,
    ]

    assert data.bands == [
        [-2.0, -1.5, -1.0],
        [1.0, 1.5, 2.0],
    ]


def test_estimate_band_gap():

    bands = [
        [-2.0, -1.5, -1.0],
        [1.0, 1.5, 2.0],
    ]

    gap = estimate_band_gap(
        bands,
        fermi_energy=0.0,
    )

    assert gap == 2.0


def test_estimate_band_gap_metallic():

    bands = [
        [-1.0, -0.5, 0.0, 0.5, 1.0],
    ]

    gap = estimate_band_gap(
        bands,
        fermi_energy=0.0,
    )

    assert gap == 0.0


# ============================================================
# ELECTRONIC INTERPRETATION
# ============================================================


def test_interpret_unknown_gap():

    result = interpret_band_gap(None)

    assert isinstance(
        result,
        ElectronicInterpretation,
    )

    assert result.classification == "unknown"
    assert result.band_gap is None


def test_interpret_metallic():

    result = interpret_band_gap(
        0.01
    )

    assert (
        result.classification
        == "metallic_or_semimetallic"
    )

    assert result.band_gap == 0.01


def test_interpret_semiconductor():

    result = interpret_band_gap(
        1.50
    )

    assert (
        result.classification
        == "semiconductor"
    )

    assert result.band_gap == 1.50


def test_interpret_insulator():

    result = interpret_band_gap(
        4.00
    )

    assert (
        result.classification
        == "insulator"
    )

    assert result.band_gap == 4.00
