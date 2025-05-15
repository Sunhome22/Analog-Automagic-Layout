# ==================================================================================================================== #
# Copyright (C) 2025 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #


# ================================================== Libraries =========================================================
import os
import re
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict
from logger.logger import get_a_logger
import gdspy

# ================================================= LVS checker ========================================================


class LayoutToSVG:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))
        self.project_directory = project_properties.directory
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_cell_name = project_properties.top_cell_name

    def create_custom_svg_from_layout_cell(self, cell):
        """This function is not general in the slightest, and was just created to make pretty pictures"""

        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        # Runs GDS command from work directory of project
        try:
            output = subprocess.run([f'make gds CELL={cell}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True, shell=True, cwd=work_directory)
            self.logger.info(output.stdout)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'make gds CELL={cell}' command had problems: {e.stderr}")

        lib = gdspy.GdsLibrary()
        lib.read_gds(f'{work_directory}gds/{cell}.gds')
        top_cell = lib.top_level()[0]
        visual_cell = gdspy.Cell("VISUAL_TOP")

        # Add top-level polygons
        for polygon in top_cell.polygons:
            visual_cell.add(polygon)

        # Replace sub-cells with bounding box and label
        for ref in top_cell.references:
            bbox = ref.get_bounding_box()
            if bbox is not None:
                x0, y0 = bbox[0]
                x1, y1 = bbox[1]

                rect = gdspy.Rectangle((x0, y0), (x1, y1), layer=999, datatype=0)
                visual_cell.add(rect)

                label = gdspy.Label(
                    ref.ref_cell.name,
                    position=((x0 + x1) / 2, (y0 + y1) / 2),
                    anchor='lower center',
                    layer=998,
                    texttype=0,
                    magnification=0.28
                )
                visual_cell.add(label)

        for label in top_cell.labels:
            # Specific port layers
            if label.layer == 69 or label.layer == 67:
                visual_cell.add(gdspy.Label(
                    label.text,
                    position=label.position,
                    layer=997,
                    texttype=0,
                    anchor='middle center',
                    magnification=0.4
                ))

        visual_cell.write_svg(f"src/utils/{cell}.svg", background='#ffffff', pad=10)

        with open(f"src/utils/{cell}.svg", "r") as f:
            svg_content = f.read()

        # Regex pattern to match the unwanted <style> block
        svg_content = re.sub(
            r'<style\s+type="text/css">\s*\.l94d20\s*\{[^}]*\}.*?</style>',
            '',
            svg_content,
            flags=re.DOTALL
        )

        # Custom CSS color format
        new_style = """
        <defs>
        <style type="text/css">
          /* Highlighted layers */
          .l70d20 { fill: #1f77b4; fill-opacity: 0.7; }    /* Metal2 (blue) */
          .l69d20 { fill: #d62728; fill-opacity: 0.7; }    /* Metal3 (red) */
          .l67d20 { fill: #56423e; fill-opacity: 0.7; }    /* Metal1 (brown) */
          .l68d20 { fill: #bea6a1; fill-opacity: 0.7; }    /* Locali (light brown) */
          .l68d44 { fill: #0077ff;}                        /* via1 (bright blue) */
          .l67d44 { fill: #e09a8e;}                        /* viali (red shade) */
          .l69d44 { fill: #70b512;}                        /* via2 (green) */
          /* Not dealt with */
          .l64d20,
          .l65d20,
          .l65d44,
          .l66d13,
          .l66d20,
          .l66d44,
          .l67d16,
          .l68d16,
          .l69d16,
          .l86d20,
          .l93d44,
          .l94d20,
          .l95d20,
          .l235d4 {
            fill: #000000;
            fill-opacity: 0.0;
          }
          /* Subcell box */
          .l998t0 { fill: #F5F5F5; font-size: 16px;}
          .l997t0 { fill: #000000; font-size: 16px;}
          .l999d0 { stroke: #000000; stroke-width: 0.7; fill: #000000; fill-opacity: 0.2; }
        </style>
        </defs>
        """
        # Insert the new style inside <svg> tag after it opens
        if "<defs>" in svg_content:
            # Replace existing <defs> contents or just add at start of <defs>
            svg_content = re.sub(r'(<defs[^>]*>)', r'\1' +
                                 new_style.replace('<defs>', '').replace('</defs>', ''),
                                 svg_content, count=1)
        else:
            pos = svg_content.find('>')
            if pos != -1:
                svg_content = svg_content[:pos + 1] + new_style + svg_content[pos + 1:]

        with open(f"src/utils/{cell}.svg", "w") as f:
            f.write(svg_content)

        self.logger.info(f"Created '{cell}.svg' in folder 'src/utils/{cell}.svg'")


def recursive_bbox(cell, visited=None):
    if visited is None:
        visited = set()
    if cell in visited:
        return None
    visited.add(cell)

    bboxes = []

    if cell.get_bounding_box() is not None:
        bboxes.append(cell.get_bounding_box())

    for ref in cell.references:
        sub_bbox = recursive_bbox(ref.ref_cell, visited)
        if sub_bbox is not None:
            ref_matrix = ref.get_transform()
            transformed_bbox = gdspy.rectangle(*sub_bbox).apply_transform(ref_matrix).get_bounding_box()
            bboxes.append(transformed_bbox)

    if not bboxes:
        return None
    else:
        all_x0 = min(b[0][0] for b in bboxes)
        all_y0 = min(b[0][1] for b in bboxes)
        all_x1 = max(b[1][0] for b in bboxes)
        all_y1 = max(b[1][1] for b in bboxes)
        return [(all_x0, all_y0), (all_x1, all_y1)]
