from __future__ import annotations

from dataclasses import dataclass, field

from hydromatai.core.material import Material
from hydromatai.ml.features import MaterialFeatures, extract_features


@dataclass(frozen=True)
class DatasetRow:
    """Une observation ML : matériau + features + cible optionnelle."""

    material_name: str
    formula: str
    features: MaterialFeatures
    target: float | None = None

    @property
    def feature_vector(self) -> tuple[float, ...]:
        """Vecteur numérique utilisable par un futur modèle."""
        return self.features.as_vector


@dataclass
class MaterialDataset:
    """Dataset de matériaux destiné aux futurs modèles ML."""

    rows: list[DatasetRow] = field(default_factory=list)

    def add_material(
        self,
        material: Material,
        target: float | None = None,
    ) -> DatasetRow:
        """Ajoute un matériau au dataset."""
        features = extract_features(material)

        row = DatasetRow(
            material_name=material.name,
            formula=material.formula,
            features=features,
            target=target,
        )

        self.rows.append(row)
        return row

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def feature_matrix(self) -> list[tuple[float, ...]]:
        """Retourne la matrice X sous forme de liste de vecteurs."""
        return [row.feature_vector for row in self.rows]

    @property
    def targets(self) -> list[float | None]:
        """Retourne les cibles y."""
        return [row.target for row in self.rows]

    def supervised_rows(self) -> list[DatasetRow]:
        """Retourne uniquement les observations possédant une cible."""
        return [row for row in self.rows if row.target is not None]
