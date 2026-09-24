from hydromatai.aida import AIDA, evidence, render_report


def test_aida_import_and_analysis():
    agent = AIDA()

    result = agent.analyze(
        "TiFeH2",
        [
            evidence(
                "H2_capacity",
                1.86,
                "literature/TiFeH2",
                status="LITERATURE",
                category="LITERATURE",
            )
        ],
    )

    assert result.subject == "TiFeH2"
    assert len(result.findings) == 1
    assert result.findings[0].evidence[0].value == 1.86


def test_aida_report():
    agent = AIDA()

    result = agent.analyze("TiFeH2")

    report = render_report(result)

    assert "AIDA SCIENTIFIC ANALYSIS" in report
    assert "TiFeH2" in report
    assert "Aucune preuve" in report
