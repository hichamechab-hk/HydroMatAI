from pathlib import Path

from hydromatai.scientific import ScientificWorkflow, write_scientific_report


def test_scientific_report_contains_published_results(tmp_path: Path):
    workflow = ScientificWorkflow()
    result = workflow.run("NU-1501-Al")

    report_path = tmp_path / "scientific_report.txt"

    returned_path = write_scientific_report(
        result,
        report_path,
    )

    assert returned_path == report_path
    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    assert "Published literature:" in text
    assert "bet_surface_area" in text
    assert "7310.0 m2/g" in text
    assert "h2_uptake" in text
    assert "14.5 wt%" in text
    assert "10.1126/science.aaz8881" in text


def test_scientific_report_without_literature(tmp_path: Path):
    workflow = ScientificWorkflow()
    result = workflow.run("UNKNOWN-MATERIAL")

    report_path = tmp_path / "empty_report.txt"

    write_scientific_report(
        result,
        report_path,
    )

    text = report_path.read_text(encoding="utf-8")

    assert "No published results available." in text
