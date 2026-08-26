"""Optical properties."""

from .dielectric import (
    DielectricData,
    read_dielectric_file,
    refractive_index,
    extinction_coefficient,
    reflectivity,
    energy_loss_function,
)

from .optical import calculate_optical_properties

from .analyzer import (
    OpticalInterpretation,
    interpret_optical_data,
    analyze_optical,
)

from .result import OpticalResult

from .workflow import OpticalWorkflow


__all__ = [
    "DielectricData",
    "OpticalResult",
    "OpticalWorkflow",
    "read_dielectric_file",
    "calculate_optical_properties",
    "energy_loss_function",
    "analyze_optical",
]
