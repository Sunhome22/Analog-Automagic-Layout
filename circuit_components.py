from dataclasses import dataclass, field
from typing import List, Dict

# ============================================= Circuit component classes ==============================================

@dataclass
class LayoutPorts:
    type: str
    layer: str
    size_cords: List[int] # x1, x2, y1, y2

@dataclass
class CircuitComponent:
    name: str = field(default_factory=str)
    schematic_connections: Dict[str, str] = field(default_factory=Dict[str, str])
    layout_name: str = field(default_factory=str)
    layout_library: str = field(default_factory=str)
    layout_ports: List[LayoutPorts] = field(default_factory=list)
    t_matrix: List[int] = field(default_factory=list[int])
    b_box: List[int] = field(default_factory=list[int])

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

@dataclass
class Pin:
    type: str
    name: str

@dataclass
class SubCircuit:
    layout_name: str
    ports: List[str]



