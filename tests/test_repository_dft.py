from hydromatai.database import MaterialRecord, MaterialRepository
from hydromatai.dft import DFTResult


def test_repository_persists_dft_result():

    repository = MaterialRepository()

    material = MaterialRecord(
        formula="TiO2",
        name="Titanium dioxide",
        dft_result=DFTResult(
            success=True,
            total_energy=-10.5,
            band_gap=2.1,
        ),
    )

    repository.add(material)

    new_repository = MaterialRepository()

    result = new_repository.get_by_formula("TiO2")

    assert result is not None
    assert result.formula == "TiO2"
    assert result.dft_result is not None
    assert result.dft_result.success is True
    assert result.dft_result.total_energy == -10.5
    assert result.dft_result.band_gap == 2.1
