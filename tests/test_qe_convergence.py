from hydromatai.dft.validation import QEConvergenceAnalyzer


def test_qe_convergence_success():

    output = """
    iteration # 1
    iteration # 2
    iteration # 3

    convergence has been achieved in 3 iterations

    !    total energy              =   -123.456789 Ry

    JOB DONE.
    """

    result = QEConvergenceAnalyzer().analyze(output)

    assert result.converged is True
    assert result.job_done is True
    assert result.scf_iterations == 3
    assert result.total_energy == -123.456789
    assert result.error_type is None


def test_qe_convergence_failure():

    output = """
    iteration # 1
    iteration # 2

    convergence NOT achieved
    """

    result = QEConvergenceAnalyzer().analyze(output)

    assert result.converged is False
    assert result.job_done is False
    assert result.scf_iterations == 2
    assert result.error_type == "CONVERGENCE"


def test_qe_memory_failure():

    output = """
    iteration # 1

    Error in routine c_bands
    cannot allocate memory
    """

    result = QEConvergenceAnalyzer().analyze(output)

    assert result.converged is False
    assert result.error_type == "MEMORY"


def test_qe_empty_output():

    result = QEConvergenceAnalyzer().analyze("")

    assert result.converged is False
    assert result.job_done is False
    assert result.error_type == "EMPTY_OUTPUT"
