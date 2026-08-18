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
        et le persiste dans la base.
        """

        if not isinstance(material, MaterialRecord):
            raise TypeError(
                "material must be a MaterialRecord"
            )

        record = MaterialModel(
            name=material.name or material.formula,
            formula=material.formula,
        )

        self.session.add(record)
        self.session.commit()

        self._records.append(material)

        return material

    def get_by_formula(self, formula: str):
        """
        Recherche un matériau par formule chimique.
        """

        # Retourner le même objet si déjà chargé
        for material in self._records:
            if material.formula == formula:
                return material

        # Sinon, rechercher dans SQLite
        record = (
            self.session
            .query(MaterialModel)
            .filter(MaterialModel.formula == formula)
            .first()
        )

        if record is None:
            return None

        material = MaterialRecord(
            formula=record.formula,
            name=record.name,
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

        self._records = [
            MaterialRecord(
                formula=record.formula,
                name=record.name,
            )
            for record in records
        ]

        return list(self._records)
