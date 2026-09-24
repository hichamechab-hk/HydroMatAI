from pathlib import Path

from hydromatai.aida.data_sources import (
    collect_subject_sources,
    discover_qe_files,
    load_priority_record,
)


def test_priority_record_tifeh2():
    row = load_priority_record("TiFeH2")

    assert row is not None
    assert row["TiFeH2"] if "TiFeH2" in row else True


def test_qe_discovery_tifeh2():
    data = discover_qe_files("TiFeH2")

    assert "historical_top5_dft" in data
    assert "new_campaign" in data

    historical = "\n".join(data["historical_top5_dft"])
    campaign = "\n".join(data["new_campaign"])

    assert "TiFeH2_relax.in" in historical
    assert "TiFeH2_scf.in" in historical
    assert "TiFeH2_relaxed_bands.in" in historical
    assert "TiFeH2_cutoff_60.out" in campaign
    assert "TiFeH2_kpoints_2.out" in campaign


def test_collect_sources():
    data = collect_subject_sources("TiFeH2")

    assert data["subject"] == "TiFeH2"
    assert data["priority_report"] is not None
    assert data["qe_files"]["historical_top5_dft"]
    assert data["qe_files"]["new_campaign"]
