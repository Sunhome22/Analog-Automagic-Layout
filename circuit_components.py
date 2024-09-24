from dataclasses import dataclass, field
from typing import List, Dict

# ============================================= Circuit component classes ==============================================
@dataclass
class CircuitComponent:
    name: str
    connections: Dict[str, str]
    layout_name: str

@dataclass
class SubCircuit:
    layout: str
    ports: List[str]

@dataclass
class Transistor(CircuitComponent):
    library: str
    t_matrix: List[int] = field(default_factory=list)
    b_box: List[int] = field(default_factory=list)



@dataclass
class Resistor(CircuitComponent):
    library: str
    t_matrix: List[int] = field(default_factory=list)
    b_box: List[int] = field(default_factory=list)


@dataclass
class Capacitor(CircuitComponent):
    library: str
    t_matrix: List[int] = field(default_factory=list)
    b_box: List[int] = field(default_factory=list)


@dataclass
class SKY130Capacitor(CircuitComponent):
    width: int
    length: int
    multiplier_factor: int
    instance_multiplier: int
    t_matrix: List[int] = field(default_factory=list)
    b_box: List[int] = field(default_factory=list)


@dataclass
class SKY130Resistor(CircuitComponent):
    width: float
    length: float
    multiplier_factor: int
    instance_multiplier: int
    t_matrix: List[int] = field(default_factory=list)
    b_box: List[int] = field(default_factory=list)


@dataclass
class Pin:
    type: str
    name: str

