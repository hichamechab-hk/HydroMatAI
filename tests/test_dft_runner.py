from pathlib import Path

from hydromatai.dft.runner import DFTRunner


def test_dft_runner(tmp_path: Path):

    runner = DFTRunner(
        ["python", "-c", "print('DFT TEST OK')"]
    )

    output = runner.run(tmp_path)

    assert "DFT TEST OK" in output
