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
class CircuitCell:
    name: str
    ports: List[str]


@dataclass
class SubCircuit:
    layout_name: str
    ports: List[str]


@dataclass
class Pin:
    instance: str = field(default_factory=str)
    number_id: int = field(default_factory=int)
    cell: str = field(default_factory=str)
    type: str = field(default_factory=str)
    name: str = field(default_factory=str)


@dataclass
class LayoutPort:
    type: str = field(default_factory=str)
    layer: str = field(default_factory=str)
    area: RectArea = field(default_factory=RectArea)

    # Handling of JSON file input
    def __post_init__(self):
        if isinstance(self.area, dict):
            self.area = RectArea(**self.area)

# ============================================= Circuit component classes ==============================================


@dataclass
class CircuitComponent:
    instance: str = field(default_factory=str)
    number_id: int = field(default_factory=int)
    name: str = field(default_factory=str)
    cell: str = field(default_factory=str)
    group: str = field(default_factory=str)
    schematic_connections: dict = field(default_factory=dict)
    layout_name: str = field(default_factory=str)
    layout_library: str = field(default_factory=str)
    layout_ports: List[LayoutPort] = field(default_factory=list) # | dict
    transform_matrix: TransformMatrix = field(default_factory=TransformMatrix) # | dict
    bounding_box: RectArea = field(default_factory=RectArea) # | dict


    # Handling of JSON file input
    def __post_init__(self):

        if isinstance(self.layout_ports, list):
            self.layout_ports = [LayoutPort(**rank) for rank in self.layout_ports]

        if isinstance(self.bounding_box, dict):
            self.bounding_box = RectArea(**self.bounding_box)

        if isinstance(self.transform_matrix, dict):
            self.transform_matrix = TransformMatrix(**self.transform_matrix)


@dataclass
class Transistor(CircuitComponent):
    pass


@dataclass
class Resistor(CircuitComponent):
    pass


@dataclass
class Capacitor(CircuitComponent):
    pass








