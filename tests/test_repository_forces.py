from hydromatai.database import MaterialRecord, MaterialRepository
from hydromatai.dft import DFTResult


def test_repository_persists_dft_forces():

    repository = MaterialRepository()

    material = MaterialRecord(
        formula="TiO2",
        name="Titanium dioxide",
        dft_result=DFTResult(
            success=True,
            total_energy=-10.5,
            band_gap=2.1,
            forces=[
                [0.1, 0.2, 0.3],
                [-0.1, -0.2, -0.3],
            ],
        ),
    )

    repository.add(material)

    new_repository = MaterialRepository()

    result = new_repository.get_by_formula("TiO2")

    assert result is not None
    assert result.dft_result is not None
    assert result.dft_result.forces == [
        [0.1, 0.2, 0.3],
        [-0.1, -0.2, -0.3],
    ]
