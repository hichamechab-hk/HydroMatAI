from pathlib import Path

from hydromatai.platform.workflow import PlatformWorkflow
from hydromatai.reports.property_report import create_report


def test_platform_workflow():

    workflow = PlatformWorkflow(
        material="CH4",
        dry_run=True,
    )

    description = workflow.describe()

    assert description["material"] == "CH4"
    assert description["dry_run"] is True
    assert description["real_dft"] is False

    result = workflow.run()

    assert result.success is True
    assert result.material == "CH4"

    assert result.stages_completed == [
        "discovery",
        "dft",
        "electronic",
        "optical",
        "scientific",
        "report",
    ]


def test_platform_result_summary():

    workflow = PlatformWorkflow(
        material="CH4",
        dry_run=True,
    )

    result = workflow.run()

    summary = result.summary()

    assert "HydroMatAI Platform" in summary
    assert "CH4" in summary
    assert "SUCCESS" in summary


def test_create_scientific_report(tmp_path: Path):

    output = tmp_path / "report.txt"

    result = create_report(
        output,
        title="HydroMatAI Test Report",
        electronic_text="Band gap = 1.50 eV",
        optical_text="Reflectivity calculated",
        convergence_text="RELAX and SCF converged",
    )

    assert result == output
    assert output.exists()

    text = output.read_text(
        encoding="utf-8"
    )

    assert "HydroMatAI Test Report" in text
    assert "Band gap = 1.50 eV" in text
    assert "Reflectivity calculated" in text
    assert "RELAX and SCF converged" in text
