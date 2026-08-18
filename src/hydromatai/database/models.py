from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class MaterialRecord(Base):
    """
    Modèle de stockage d'un matériau HydroMatAI.
    """

    __tablename__ = "materials"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(100),
        nullable=False
    )

    formula = Column(
        String(100),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    density = Column(
        Float,
        nullable=True
    )

    band_gap = Column(
        Float,
        nullable=True
    )


    def __repr__(self):
        return (
            f"<MaterialRecord "
            f"name={self.name}, "
            f"formula={self.formula}>"
        )
