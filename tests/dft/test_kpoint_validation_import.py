from hydromatai.dft.validation import (
    KPointResult,
    energy_spread,
    parse_kpoint_output,
    successive_energy_differences,
)


def test_kpoint_validation_public_api():
    assert KPointResult is not None
    assert callable(parse_kpoint_output)
    assert callable(energy_spread)
    assert callable(successive_energy_differences)
