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

from matplotlib import pyplot as plt, patches
from circuit.circuit_components import Pin, CircuitCell, TraceNet
import os


def draw_result(grid_size, objects, connections, used_area, scale_factor, draw_name):
    current_file_directory = os.path.dirname(os.path.abspath(__file__))
    # set up plot
    fix, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)

    # draw grid
    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell, Trace)):

            rect = patches.Rectangle((obj.transform_matrix.c, obj.transform_matrix.f),
                                     obj.bounding_box.x2, obj.bounding_box.y2,
                                     linewidth=1, edgecolor='blue', facecolor='red')
            ax.add_patch(rect)
            ax.text(obj.transform_matrix.c + (obj.bounding_box.x2 / 2),
                    obj.transform_matrix.f + (obj.bounding_box.y2 / 2), obj.group+"_"+obj.name,
                    ha='center', va='center', fontsize=12, color='black')

    plt.title('OBJ placement')
    plt.savefig(f"{current_file_directory}/test_placement.png")