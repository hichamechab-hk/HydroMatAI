from .models import MaterialRecord
from .storage import get_session


class MaterialRepository:
    """
    Gestion des matériaux dans HydroMatAI.
    """


    def __init__(self):
        self.session = get_session()


    def add(self, material):
        """
        Ajoute un matériau.
        """

        record = MaterialRecord(
            name=material["name"],
            formula=material["formula"],
            description=material.get("description"),
            density=material.get("density"),
            band_gap=material.get("band_gap")
        )

        self.session.add(record)
        self.session.commit()

        return record



    def get_by_formula(self, formula):
        """
        Recherche par formule chimique.
        """

        return (
            self.session
            .query(MaterialRecord)
            .filter(
                MaterialRecord.formula == formula
            )
            .all()
        )



    def list_all(self):
        """
        Liste tous les matériaux.
        """

        return (
            self.session
            .query(MaterialRecord)
            .all()
        )
