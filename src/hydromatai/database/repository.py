from hydromatai.dft import DFTResult

from .models import MaterialModel
from .record import MaterialRecord
from .storage import get_session


class MaterialRepository:
    """
    Gestion des matériaux dans HydroMatAI.
    """

    def __init__(self):
        self.session = get_session()
        self._records = []

    def add(self, material: MaterialRecord):
        """
        Ajoute un MaterialRecord dans le repository
        et le persiste dans la base SQLite.
        """

        if not isinstance(material, MaterialRecord):
            raise TypeError(
                "material must be a MaterialRecord"
            )

        dft_result = material.dft_result

        record = MaterialModel(
            name=material.name or material.formula,
            formula=material.formula,
            dft_success=(
                int(dft_result.success)
                if dft_result is not None
                else None
            ),
            total_energy=(
                dft_result.total_energy
                if dft_result is not None
                else None
            ),
            band_gap=(
                dft_result.band_gap
                if dft_result is not None
                else None
            ),
            forces=(
                dft_result.forces
                if dft_result is not None
                else None
            ),
        )

        self.session.add(record)
        self.session.commit()

        self._records.append(material)

        return material

    def get_by_formula(self, formula: str):
        """
        Recherche un matériau par formule chimique.
        """

        for material in self._records:
            if material.formula == formula:
                return material

        record = (
            self.session
            .query(MaterialModel)
            .filter(MaterialModel.formula == formula)
            .order_by(MaterialModel.id.desc())
            .first()
        )

        if record is None:
            return None

        dft_result = None

        if record.dft_success is not None:
            dft_result = DFTResult(
                success=bool(record.dft_success),
                total_energy=record.total_energy,
                band_gap=record.band_gap,
                forces=record.forces,
            )

        material = MaterialRecord(
            formula=record.formula,
            name=record.name,
            dft_result=dft_result,
        )

        self._records.append(material)

        return material

    def list_all(self):
        """
        Retourne tous les matériaux.
        """

        if self._records:
            return list(self._records)

        records = (
            self.session
            .query(MaterialModel)
            .all()
        )

        self._records = []

        for record in records:
            dft_result = None

            if record.dft_success is not None:
                dft_result = DFTResult(
                    success=bool(record.dft_success),
                    total_energy=record.total_energy,
                    band_gap=record.band_gap,
                    forces=record.forces,
                )

            material = MaterialRecord(
                formula=record.formula,
                name=record.name,
                dft_result=dft_result,
            )

            self._records.append(material)

        return list(self._records)
