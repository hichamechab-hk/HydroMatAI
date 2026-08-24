"""Optical properties."""

from .dielectric import (
    DielectricData,
    read_dielectric_file,
    refractive_index,
    extinction_coefficient,
    reflectivity,
)

from .optical import calculate_optical_properties
from .analyzer import OpticalInterpretation, interpret_optical_data

__all__ = [
    "DielectricData",
    "read_dielectric_file",
    "refractive_index",
    "extinction_coefficient",
    "reflectivity",
    "calculate_optical_properties",
    "OpticalInterpretation",
    "interpret_optical_data",
]
