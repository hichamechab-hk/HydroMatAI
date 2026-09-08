from pathlib import Path

import pytest

from hydromatai.literature import (
    LiteratureRepository,
    LiteratureResult,
    import_literature_csv,
)


def test_literature_result():
    result = LiteratureResult(
        material="NU-1501-Al",
        property_name="hydrogen_uptake",
        value=14.0,
        unit="wt%",
        title="Hydrogen storage in porous materials",
        authors=["Author A", "Author B"],
        year=2024,
        doi="10.1234/example",
        method="DFT+GCMC",
    )

    assert result.material == "NU-1501-Al"
    assert result.value == 14.0
    assert result.source_type == "literature"
    assert result.year == 2024


def test_invalid_material():
    with pytest.raises(ValueError):
        LiteratureResult(
            material="",
            property_name="band_gap",
            value=1.0,
            unit="eV",
        )


def test_repository():
    repository = LiteratureRepository()

    result = LiteratureResult(
        material="NU-1501-Al",
        property_name="band_gap",
        value=1.5,
        unit="eV",
    )

    repository.add(result)

    assert len(repository) == 1
    assert repository.for_material("NU-1501-Al") == [result]
    assert repository.for_property("band_gap") == [result]


def test_import_csv(tmp_path: Path):
    csv_file = tmp_path / "literature.csv"

    csv_file.write_text(
        "material,property,value,unit,title,authors,year,doi,method\n"
        "NU-1501-Al,hydrogen_uptake,14.0,wt%,"
        "Hydrogen Storage,Author A;Author B,2024,10.1234/example,DFT+GCMC\n",
        encoding="utf-8",
    )

    results = import_literature_csv(csv_file)

    assert len(results) == 1
    assert results[0].material == "NU-1501-Al"
    assert results[0].value == 14.0
    assert results[0].authors == ["Author A", "Author B"]
    assert results[0].year == 2024
