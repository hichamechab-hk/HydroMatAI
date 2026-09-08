from __future__ import annotations

from dataclasses import dataclass, field

from hydromatai.core.material import Material
from hydromatai.ml.features import MaterialFeatures, extract_features
from hydromatai.ml.targets import TargetDefinition


@dataclass(frozen=True)
class DatasetRow:
    """Une observation ML : matériau + features + cible optionnelle."""

    material_name: str
    formula: str
    features: MaterialFeatures
    target: float | None = None
    target_definition: TargetDefinition | None = None

    @property
    def feature_vector(self) -> tuple[float, ...]:
        return self.features.as_vector


@dataclass
class MaterialDataset:
    """Dataset de matériaux destiné aux futurs modèles ML."""

    rows: list[DatasetRow] = field(default_factory=list)
    target_definition: TargetDefinition | None = None

    def add_material(
        self,
        material: Material,
        target: float | None = None,
    ) -> DatasetRow:
        features = extract_features(material)

        if (
            target is not None
            and self.target_definition is not None
            and not self.target_definition.validate_value(target)
        ):
            raise ValueError(
                f"Valeur de target invalide pour "
                f"{self.target_definition.name!r}."
            )

        row = DatasetRow(
            material_name=material.name,
            formula=material.formula,
            features=features,
            target=target,
            target_definition=self.target_definition,
        )

        self.rows.append(row)
        return row

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def feature_matrix(self) -> list[tuple[float, ...]]:
        return [row.feature_vector for row in self.rows]

    @property
    def targets(self) -> list[float | None]:
        return [row.target for row in self.rows]

    def supervised_rows(self) -> list[DatasetRow]:
        return [row for row in self.rows if row.target is not None]
