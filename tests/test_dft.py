from hydromatai.dft import DFTCalculator, DFTResult


def test_dft_result():

    result = DFTResult(
        success=True,
        total_energy=-10.5,
        band_gap=2.1,
    )

    assert result.success is True
    assert result.total_energy == -10.5
    assert result.band_gap == 2.1


def test_dft_calculator_is_abstract():

    assert DFTCalculator.__abstractmethods__ == {
        "prepare_input",
        "run",
        "parse_output",
    }
