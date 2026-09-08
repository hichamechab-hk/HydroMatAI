from pathlib import Path

from hydromatai.properties.optical import (
    DielectricData,
    OpticalResult,
    OpticalWorkflow,
    absorption_coefficient,
    calculate_optical_properties,
    energy_loss_function,
    extinction_coefficient,
    interpret_optical_data,
    read_dielectric_file,
    reflectivity,
    refractive_index,
)


def test_dielectric_data():

    data = DielectricData(
        energy=[1.0, 2.0],
        epsilon_real=[4.0, 9.0],
        epsilon_imag=[0.0, 0.0],
    )

    assert data.energy == [1.0, 2.0]
    assert data.epsilon_real == [4.0, 9.0]
    assert data.epsilon_imag == [0.0, 0.0]


def test_read_dielectric_file(tmp_path: Path):

    path = tmp_path / "dielectric.dat"

    path.write_text(
        """
# energy epsilon_real epsilon_imag
1.0 4.0 0.5
2.0 9.0 1.0
invalid line
3.0 16.0 2.0
""",
        encoding="utf-8",
    )

    data = read_dielectric_file(path)

    assert data.energy == [1.0, 2.0, 3.0]
    assert data.epsilon_real == [4.0, 9.0, 16.0]
    assert data.epsilon_imag == [0.5, 1.0, 2.0]


def test_refractive_index():

    n = refractive_index(
        4.0,
        0.0,
    )

    assert n == 2.0


def test_extinction_coefficient():

    k = extinction_coefficient(
        4.0,
        0.0,
    )

    assert k == 0.0


def test_reflectivity():

    r = reflectivity(
        4.0,
        0.0,
    )

    assert r == 1.0 / 9.0


def test_energy_loss_function():

    loss = energy_loss_function(
        2.0,
        1.0,
    )

    assert loss == 0.2


def test_absorption_zero_energy():

    alpha = absorption_coefficient(
        0.0,
        4.0,
        1.0,
    )

    assert alpha == 0.0


def test_calculate_optical_properties():

    data = DielectricData(
        energy=[1.0, 2.0],
        epsilon_real=[4.0, 9.0],
        epsilon_imag=[0.5, 1.0],
    )

    result = calculate_optical_properties(data)

    assert result["energy"] == [1.0, 2.0]
    assert len(result["refractive_index"]) == 2
    assert len(result["extinction_coefficient"]) == 2
    assert len(result["reflectivity"]) == 2
    assert len(result["absorption_coefficient"]) == 2
    assert len(result["energy_loss"]) == 2


def test_interpret_optical_data():

    result = interpret_optical_data(
        [1.0, 2.0, 3.0],
        [0.1, 2.0, 0.5],
    )

    assert result.absorption_peak_energy == 2.0
    assert result.dielectric_peak_energy == 2.0


def test_interpret_optical_data_empty():

    result = interpret_optical_data(
        [],
        [],
    )

    assert result.absorption_peak_energy is None
    assert result.dielectric_peak_energy is None


def test_optical_workflow(tmp_path: Path):

    path = tmp_path / "optical.dat"

    path.write_text(
        """
# energy epsilon_real epsilon_imag
1.0 4.0 0.5
2.0 9.0 2.0
3.0 16.0 0.5
""",
        encoding="utf-8",
    )

    workflow = OpticalWorkflow()

    result = workflow.analyze_file(path)

    assert isinstance(
        result,
        OpticalResult,
    )

    assert result.success is True
    assert result.points == 3
    assert result.classification == "optically_active"
    assert result.dielectric_peak_energy == 2.0
    assert result.loss_peak_energy is not None


def test_optical_result():

    result = OpticalResult(
        success=True,
        points=10,
        classification="optically_active",
    )

    assert result.success is True
    assert result.points == 10
    assert result.metadata == {}
