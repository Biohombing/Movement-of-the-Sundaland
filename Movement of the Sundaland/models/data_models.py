"""
models/data_models.py
Clean dataclass-based data structures for Sundaland Motion Pro.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class ObservationPoint:
    """A geographic point to be analysed."""
    name: str
    lat:  float
    lon:  float

    def validate(self) -> tuple[bool, str]:
        """Returns (is_valid, error_message)."""
        if not (-90.0 <= self.lat <= 90.0):
            return False, f"Latitude {self.lat} keluar batas (−90 … 90)."
        if not (-180.0 <= self.lon <= 180.0):
            return False, f"Longitude {self.lon} keluar batas (−180 … 180)."
        if not self.name.strip():
            return False, "Nama titik tidak boleh kosong."
        return True, ""


@dataclass
class PlateVelocity:
    """Computed plate velocity result for one observation point."""
    name:    str
    lat:     float
    lon:     float
    vN:      float   # North component (mm/yr)
    vE:      float   # East  component (mm/yr)
    vT:      float   # Total magnitude (mm/yr)
    azimuth: float   # 0–360 degrees
    compass: str     # 16-point compass (Indonesian)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def speed_label(self) -> str:
        return f"{self.vT:.2f} mm/yr"

    @property
    def az_label(self) -> str:
        return f"{self.azimuth:.1f}°"


@dataclass
class EulerPoleParams:
    """Parameters of an Euler Pole."""
    name:   str
    source: str
    lat:    float
    lon:    float
    omega:  float   # deg/Ma
    frame:  str
    ref:    str = ""

    @property
    def summary(self) -> str:
        return (
            f"{self.source} | "
            f"φ={self.lat}°N  λ={abs(self.lon)}°{'W' if self.lon < 0 else 'E'} | "
            f"ω={self.omega}°/Ma | {self.frame}"
        )


@dataclass
class ProjectData:
    """
    Container for all project state.
    Easily serialisable to JSON for save/load feature.
    """
    points:  List[ObservationPoint] = field(default_factory=list)
    results: List[PlateVelocity]    = field(default_factory=list)
    notes:   str                    = ""
    version: str                    = "1.0"

    def clear_results(self):
        self.results = []

    def add_point(self, point: ObservationPoint):
        self.points.append(point)

    def remove_point(self, index: int):
        if 0 <= index < len(self.points):
            self.points.pop(index)

    def to_records(self) -> List[dict]:
        """Flatten results to list of dicts (for Excel export)."""
        return [r.to_dict() for r in self.results]
