from sqlalchemy import Column, Integer, String, Float, Text, JSON
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class MaterialModel(Base):
    """
    Modèle SQLAlchemy pour le stockage d'un matériau.
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

    dft_success = Column(
        Integer,
        nullable=True
    )

    total_energy = Column(
        Float,
        nullable=True
    )

    forces = Column(
        JSON,
        nullable=True
    )
    def __repr__(self):
        return (
            f"<MaterialModel "
            f"name={self.name}, "
            f"formula={self.formula}>"
        )






























