"""Optical-property analysis."""

from .dielectric import (
    DielectricData,
    absorption_coefficient,
    energy_loss_function,
    extinction_coefficient,
    read_dielectric_file,
    reflectivity,
    refractive_index,
)

from .optical import calculate_optical_properties

from .analyzer import (
    OpticalInterpretation,
    analyze_optical,
    interpret_optical_data,
)

from .result import OpticalResult

from .workflow import OpticalWorkflow


__all__ = [
    "DielectricData",
    "OpticalResult",
    "OpticalWorkflow",
    "OpticalInterpretation",
    "read_dielectric_file",
    "calculate_optical_properties",
    "refractive_index",
    "extinction_coefficient",
    "reflectivity",
    "absorption_coefficient",
    "energy_loss_function",
    "interpret_optical_data",
    "analyze_optical",
]
