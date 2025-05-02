# ==================================================================================================================== #
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

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
class RectAreaLayer:
    layer: str = field(default_factory=str)
    area: RectArea = field(default_factory=RectArea)

    # Handling of JSON file input
    def __post_init__(self):
        if isinstance(self.area, dict):
            self.area = RectArea(**self.area)


@dataclass
class OverlapDistance:
    x: int = field(default_factory=int)
    y: int = field(default_factory=int)


@dataclass
class SubCircuit:
    layout_name: str
    ports: List[str]


@dataclass
class LayoutPort:
    type: str = field(default_factory=str)
    layer: str = field(default_factory=str)
    area: RectArea = field(default_factory=RectArea)

    # Handling of JSON file input
    def __post_init__(self):
        if isinstance(self.area, dict):
            self.area = RectArea(**self.area)

# =========================================== Functional Component classes =============================================


@dataclass
class FunctionalComponent:
    instance: str = field(default_factory=str)
    number_id: int = field(default_factory=int)
    name: str = field(default_factory=str)
    type: str = field(default_factory=str)
    cell: str = field(default_factory=str)
    named_cell: str = field(default_factory=str)
    parent_cell: str = field(default_factory=str)
    named_parent_cell: str = field(default_factory=str)
    cell_chain: str = field(default_factory=str)
    group: str = field(default_factory=str)
    schematic_connections: dict = field(default_factory=dict)
    layout_name: str = field(default_factory=str)
    layout_library: str = field(default_factory=str)
    layout_ports: List[LayoutPort] | dict = field(default_factory=list)
    transform_matrix: TransformMatrix | dict = field(default_factory=TransformMatrix)
    bounding_box: RectArea | dict = field(default_factory=RectArea)

    # Handling of JSON file input
    def __post_init__(self):

        if isinstance(self.layout_ports, list | dict):
            self.layout_ports = [LayoutPort(**item) for item in self.layout_ports]

        if isinstance(self.bounding_box, dict):
            self.bounding_box = RectArea(**self.bounding_box)

        if isinstance(self.transform_matrix, dict):
            self.transform_matrix = TransformMatrix(**self.transform_matrix)


@dataclass
class Transistor(FunctionalComponent):
    overlap_distance: OverlapDistance | dict = field(default_factory=OverlapDistance)
    group_endpoint: str = field(default_factory=str)
    group_endpoint_bounding_box: RectArea | dict = field(default_factory=RectArea)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.overlap_distance, dict):
            self.overlap_distance = OverlapDistance(**self.overlap_distance)

        if isinstance(self.group_endpoint_bounding_box, dict):
            self.group_endpoint_bounding_box = RectArea(**self.group_endpoint_bounding_box)


@dataclass
class Resistor(FunctionalComponent):
    pass


@dataclass
class Capacitor(FunctionalComponent):
    pass


@dataclass
class DigitalBlock(FunctionalComponent):
    overlap_distance: OverlapDistance | dict = field(default_factory=OverlapDistance)
    group_endpoint: str = field(default_factory=str)
    group_endpoint_bounding_box: RectArea | dict = field(default_factory=RectArea)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.overlap_distance, dict):
            self.overlap_distance = OverlapDistance(**self.overlap_distance)

        if isinstance(self.group_endpoint_bounding_box, dict):
            self.group_endpoint_bounding_box = RectArea(**self.group_endpoint_bounding_box)

# ============================================ Structural Component classes ============================================


@dataclass
class Pin:
    instance: str = field(default_factory=str)
    number_id: int = field(default_factory=int)
    cell: str = field(default_factory=str)
    named_cell: str = field(default_factory=str)
    parent_cell: str = field(default_factory=str)
    named_parent_cell: str = field(default_factory=str)
    cell_chain: str = field(default_factory=str)
    type: str = field(default_factory=str)
    name: str = field(default_factory=str)
    layout: RectAreaLayer | dict = field(default_factory=str)

    def __post_init__(self):
        if isinstance(self.layout, dict):
            self.layout = RectAreaLayer(**self.layout)


@dataclass
class TraceNet:
    instance: str = field(default_factory=str)
    name: str = field(default_factory=str)
    cell: str = field(default_factory=str)
    named_cell: str = field(default_factory=str)
    parent_cell: str = field(default_factory=str)
    named_parent_cell: str = field(default_factory=str)
    cell_chain: str = field(default_factory=str)
    segments: List[RectAreaLayer] | dict = field(default_factory=list)
    vias: List[RectAreaLayer] | dict = field(default_factory=list)

    # Handling of JSON file input
    def __post_init__(self):

        if isinstance(self.segments, list | dict):
            self.segments = [RectAreaLayer(**item) for item in self.segments]

        if isinstance(self.vias, list | dict):
            self.vias = [RectAreaLayer(**item) for item in self.vias]


@dataclass
class CircuitCell:
    instance: str = field(default_factory=str)
    number_id: int = field(default_factory=int)
    name: str = field(default_factory=str)
    cell: str = field(default_factory=str)
    named_cell: str = field(default_factory=str)
    parent_cell: str = field(default_factory=str)
    named_parent_cell: str = field(default_factory=str)
    cell_chain: str = field(default_factory=str)
    group: str = field(default_factory=str)
    schematic_connections: dict = field(default_factory=dict)
    transform_matrix: TransformMatrix | dict = field(default_factory=TransformMatrix)
    bounding_box: RectArea | dict = field(default_factory=RectArea)

    # Handling of JSON file input
    def __post_init__(self):
        if isinstance(self.bounding_box, dict):
            self.bounding_box = RectArea(**self.bounding_box)

        if isinstance(self.transform_matrix, dict):
            self.transform_matrix = TransformMatrix(**self.transform_matrix)


