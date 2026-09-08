from hydromatai.ml.targets import (
    ADSORPTION_ENERGY,
    AVAILABLE_TARGETS,
    BAND_GAP,
    TOTAL_ENERGY,
    TargetDefinition,
)


def test_target_definition():
    target = TargetDefinition(
        name="test_property",
        unit="eV",
        description="Test property",
    )

    assert target.name == "test_property"
    assert target.unit == "eV"
    assert target.description == "Test property"


def test_target_accepts_numeric_value():
    assert ADSORPTION_ENERGY.validate_value(-0.25) is True
    assert BAND_GAP.validate_value(2.5) is True


def test_target_rejects_missing_value():
    assert ADSORPTION_ENERGY.validate_value(None) is False


def test_adsorption_energy_definition():
    assert ADSORPTION_ENERGY.name == "adsorption_energy"
    assert ADSORPTION_ENERGY.unit == "eV"


def test_available_targets():
    names = {target.name for target in AVAILABLE_TARGETS}

    assert "adsorption_energy" in names
    assert "band_gap" in names
    assert "total_energy" in names


def test_total_energy_definition():
    assert TOTAL_ENERGY.name == "total_energy"
    assert TOTAL_ENERGY.unit == "eV"
