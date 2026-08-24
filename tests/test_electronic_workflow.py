from hydromatai.dft.workflow.electronic import (
    ElectronicWorkflow,
    ElectronicWorkflowResult,
)


class FakeCalculator:

    def __init__(
        self,
        output="QE OUTPUT",
        error=None,
    ):
        self.output = output
        self.error = error
        self.prepared = False
        self.ran = False

    def prepare_input(self, material):
        self.prepared = True

    def run(self):
        self.ran = True

        if self.error:
            raise RuntimeError(self.error)

        return self.output


def create_material():
    """
    Petit objet matériau minimal pour les tests.
    """

    class Material:
        name = "TiO2_test"
        formula = "TiO2"

    return Material()


def test_electronic_workflow_success():

    workflow = ElectronicWorkflow(
        nscf_calculator=FakeCalculator(),
        bands_calculator=FakeCalculator(),
        dos_calculator=FakeCalculator(),
        pdos_calculator=FakeCalculator(),
    )

    result = workflow.run(
        create_material(),
        candidate_id="TiO2_test",
    )

    assert isinstance(
        result,
        ElectronicWorkflowResult,
    )

    assert result.success is True
    assert result.status == "PASS"

    assert result.nscf_success is True
    assert result.bands_success is True
    assert result.dos_success is True
    assert result.pdos_success is True


def test_electronic_workflow_nscf_failure():

    workflow = ElectronicWorkflow(
        nscf_calculator=FakeCalculator(
            error="NSCF failed"
        ),
        bands_calculator=FakeCalculator(),
        dos_calculator=FakeCalculator(),
        pdos_calculator=FakeCalculator(),
    )

    result = workflow.run(
        create_material(),
        candidate_id="TiO2_nscf_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_NSCF"
    assert result.error_type == "NSCF"

    assert result.nscf_success is False
    assert result.bands_success is False
    assert result.dos_success is False
    assert result.pdos_success is False


def test_electronic_workflow_bands_failure():

    workflow = ElectronicWorkflow(
        nscf_calculator=FakeCalculator(),
        bands_calculator=FakeCalculator(
            error="Bands failed"
        ),
        dos_calculator=FakeCalculator(),
        pdos_calculator=FakeCalculator(),
    )

    result = workflow.run(
        create_material(),
        candidate_id="TiO2_bands_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_BANDS"
    assert result.error_type == "BANDS"

    assert result.nscf_success is True
    assert result.bands_success is False
    assert result.dos_success is False


def test_electronic_workflow_dos_failure():

    workflow = ElectronicWorkflow(
        nscf_calculator=FakeCalculator(),
        bands_calculator=FakeCalculator(),
        dos_calculator=FakeCalculator(
            error="DOS failed"
        ),
        pdos_calculator=FakeCalculator(),
    )

    result = workflow.run(
        create_material(),
        candidate_id="TiO2_dos_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_DOS"
    assert result.error_type == "DOS"

    assert result.nscf_success is True
    assert result.bands_success is True
    assert result.dos_success is False
    assert result.pdos_success is False


def test_electronic_workflow_pdos_failure():

    workflow = ElectronicWorkflow(
        nscf_calculator=FakeCalculator(),
        bands_calculator=FakeCalculator(),
        dos_calculator=FakeCalculator(),
        pdos_calculator=FakeCalculator(
            error="PDOS failed"
        ),
    )

    result = workflow.run(
        create_material(),
        candidate_id="TiO2_pdos_fail",
    )

    assert result.success is False
    assert result.status == "FAIL_PDOS"
    assert result.error_type == "PDOS"

    assert result.nscf_success is True
    assert result.bands_success is True
    assert result.dos_success is True
    assert result.pdos_success is False
