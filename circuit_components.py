# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
from dataclasses import dataclass, field
from typing import List, Dict

# ================================================ Misc. classes =======================================================

@dataclass
class TransformMatrix:
    a: int = field(default_factory=int)
    b: int = field(default_factory=int)
    c: int = field(default_factory=int)
    d: int = field(default_factory=int)
    e: int = field(default_factory=int)
    f: int = field(default_factory=int)

    def set(self, params: list):
        self.a, self.b, self.c, self.d, self.e, self.f = params


@dataclass
class RectArea:
    x1: int = field(default_factory=int)
    y1: int = field(default_factory=int)
    x2: int = field(default_factory=int)
    y2: int = field(default_factory=int)

    def set(self, params: list):
        self.x1, self.y1, self.x2, self.y2 = params


@dataclass
class SubCircuit:
    layout_name: str
    ports: List[str]


@dataclass
class Pin:
    type: str
    name: str


@dataclass
class LayoutPort:
    type: str
    layer: str
    area: RectArea

    def __init__(self, type: str, layer: str, area_params: List[int]):
        self.type = type
        self.layer = layer
        self.area = RectArea()  # Initialize area as a new RectArea instance
        self.area.set(area_params)


# ============================================= Circuit component classes ==============================================

@dataclass
class CircuitComponent:
    name: str = field(default_factory=str)
    group: str = field(default_factory=str)
    schematic_connections: Dict[str, str] = field(default_factory=Dict[str, str])
    layout_name: str = field(default_factory=str)
    layout_library: str = field(default_factory=str)
    layout_ports: List[LayoutPort] = field(default_factory=list)
    transform_matrix: TransformMatrix = field(default_factory=TransformMatrix)
    bounding_box: RectArea = field(default_factory=RectArea)


@dataclass
class Transistor(CircuitComponent):
    pass


@dataclass
class Resistor(CircuitComponent):
    pass


@dataclass
class Capacitor(CircuitComponent):
    pass


@dataclass
class SKY130Capacitor(CircuitComponent):
    width: int = field(default_factory=int)
    length: int = field(default_factory=int)
    multiplier_factor: int = field(default_factory=int)
    instance_multiplier: int = field(default_factory=int)


@dataclass
class SKY130Resistor(CircuitComponent):
    length: float = field(default_factory=float)
    multiplier_factor: int = field(default_factory=int)
    instance_multiplier: int = field(default_factory=int)





