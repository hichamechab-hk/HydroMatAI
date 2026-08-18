from hydromatai.database import MaterialRecord
from hydromatai.dft import DFTResult


def test_material_record():

    result = DFTResult(
        success=True,
        total_energy=-10.5,
        band_gap=2.1,
    )

    record = MaterialRecord(
        formula="TiO2",
        name="Titanium dioxide",
        dft_result=result,
        metadata={"source": "quantum_espresso"},
    )

    assert record.formula == "TiO2"
    assert record.name == "Titanium dioxide"
    assert record.dft_result.total_energy == -10.5
    assert record.dft_result.band_gap == 2.1
    assert record.metadata["source"] == "quantum_espresso"
    assert record.created_at is not None
