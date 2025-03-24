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
from logger.logger import get_a_logger
import tomllib

logger = get_a_logger(__name__)

def load_config(path="pyproject.toml"):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        logger.error(f"Error loading config: {e}")



config = load_config()
GRID_SIZE = config["generate_grid"]["GRID_SIZE"]
SCALE_FACTOR = config["generate_grid"]["SCALE_FACTOR"]




def draw_result( objects, connections, used_area, draw_name):
    connections2 =  [x for x in connections.values() if x is not None]

    # set up plot
    fix, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, GRID_SIZE)
    ax.set_ylim(0, GRID_SIZE)
    path = True



    # draw grid

    for i in range(GRID_SIZE + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell, TraceNet)):

            rect = patches.Rectangle((obj.transform_matrix.c, obj.transform_matrix.f), obj.bounding_box.x2, obj.bounding_box.y2, linewidth=1, edgecolor='blue', facecolor='red')

            ax.add_patch(rect)

            ax.text(obj.transform_matrix.c + (obj.bounding_box.x2 / 2), obj.transform_matrix.f + (obj.bounding_box.y2 / 2), obj.group+"_"+obj.name,
                ha='center', va='center', fontsize=12, color='black')

    if not path:
        for p in connections2:
            start = p.starting_comp
            end = p.end_comp
            x_values = []
            y_values = []

            for obj in objects:
                if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                    if obj.number_id == start:

                        x_values.append(obj.transform_matrix.c + (obj.bounding_box.x2/2))
                        y_values.append(obj.transform_matrix.f + (obj.bounding_box.y2 / 2))
                        break
            for obj in objects:
                if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                    if obj.number_id == end:
                        x_values.append(obj.transform_matrix.c + (obj.bounding_box.x2/2))
                        y_values.append(obj.transform_matrix.f + (obj.bounding_box.y2 / 2))
                        break
            plt.plot(x_values, y_values)

            plt.plot([GRID_SIZE//2, GRID_SIZE//2], [0, GRID_SIZE])
    else:
        scaled_points = []
        none = 0
        missing_paths = []
        for net in connections2:
            logger.info(connections2)
            for p in net:
                logger.info(p)
                if p[1] is not None:
                    scaled_points.append( [(used_area.x1-500 + x*SCALE_FACTOR , used_area.y1-500 + y*SCALE_FACTOR ) for x, y in p[1]])
                else:
                    missing_paths.append(p[0])
                    none += 1

        for con in scaled_points:

            x_coordinates, y_coordinates = zip(*con)
            plt.plot(x_coordinates, y_coordinates, linewidth=4, color='black')
            plt.plot(x_coordinates, y_coordinates, linewidth=2, linestyle='-')




    plt.title('OBJ placement')
    plt.savefig('results/'+draw_name+'.png')