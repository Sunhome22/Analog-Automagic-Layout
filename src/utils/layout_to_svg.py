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

import html
import sys, os, re
from klayout import db

# =============================================== Layout to SVG ========================================================


class LayoutToSVG:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties):
        self.project_directory = project_properties.directory
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_cell_name = project_properties.top_cell_name

    def create_custom_svg_from_layout_cell(self, cell):
        """Generate SVG with user instance names on boxes"""

        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        # Runs GDS command from work directory of project
        try:
            output = subprocess.run(['make', 'gds', f'CELL={cell}'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, check=True, shell=False, cwd=work_directory)
            self.logger.info(output.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"'make gds CELL={cell}' command had problems: {e.stderr}")

        # Load the GDSII file
        layout = db.Layout()
        layout.read(f"{work_directory}gds/{cell}.gds")
        top_cell = layout.cell(cell)

        # Create a (temporary) SVG file
        svg_path = f"src/utils/{cell}.svg"

        svg_elements = []
        pad = 1100

        # Collect all polygons
        for layer_index in range(layout.layers()):
            layer_info = layout.get_info(layer_index)
            ly = top_cell.layout().layer(layer_info)
            for s in top_cell.shapes(ly):
                if s.is_text():
                    self.logger.info(f"Labels: '{s.text}' is on layer={layer_info.layer}, datatype={layer_info.datatype}")

                if s.is_box() or s.is_path() or s.is_polygon():

                    if s.is_polygon():
                        region = db.Region(s.polygon)
                    elif s.is_box():
                        region = db.Region(s.box)
                    elif s.is_path():
                        region = db.Region(s.path)
                    else:
                        self.logger.warning(f"Cannot convert this Shape to a Region: {s}")
                        continue

                    for p in region.each():
                        pts = extract_points(p)
                        if not pts:
                            continue  # skip if empty
                        svg_path_str = "M " + " L ".join(f"{x},{-y}" for x, y in pts) + " Z"
                        self.logger.info(f"Found box '{svg_path_str}' in layer='{layer_info.layer}' with datatype='{layer_info.datatype}'")
                        svg_elements.append(f'<path d="{svg_path_str}" class="l{layer_info.layer}d{layer_info.datatype}" />')

        # Draw component bounding boxes and label them with user defined instance name
        for ref in top_cell.each_inst():
            bbox = ref.bbox()
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox.left, bbox.bottom, bbox.right, bbox.top
            svg_elements.append(
                f'<rect x="{x0}" y="{-y1}" width="{x1-x0}" height="{y1-y0}" class="l999d0" />'
            )
            props = ref.properties()
            raw_name = props.get(61, None) or ref.cell.name  # Needs manual updating
            inst_name = html.escape(str(raw_name) if raw_name is not None else "")
            svg_elements.append(
                f'<text x="{(x0 + x1) / 2}" y="{- (y0 + y1) / 2}" class="l998t0" text-anchor="middle" alignment-baseline="middle">{inst_name}</text>'
            )

        # Draw labels for connection port
        for layer_index in range(layout.layers()):
            layer_info = layout.get_info(layer_index)

            if layer_info.layer not in (69, 67, 8, 30):  # Needs manual updating
                continue
            ly = top_cell.layout().layer(layer_info)
            for shape in top_cell.shapes(ly):
                if shape.is_text():
                    disp = shape.text_trans.disp
                    x = disp.x
                    y = disp.y
                    label_text = next(iter(re.findall(r"'([^']+)'", str(shape.text))), str(shape.text))
                    svg_elements.append(
                        f'<text x="{x}" y="{-y + 180}" class="l997t0" text-anchor="middle" alignment-baseline="central">{label_text}</text>'
                    )

        bbox = top_cell.bbox()
        width, height = bbox.width(), bbox.height()
        min_x, min_y, max_x, max_y = bbox.left, bbox.bottom, bbox.right, bbox.top
        svg_width = width + 2*pad
        svg_height = height + 2*pad

        metal_colors = {
            "Metal1": "#56423e",
            "Metal2": "#bea6a1",
            "Metal3": "#d62728",
            "Metal4": "#1f77b4",
            "Via1": "#e09a8e",
            "Via2": "#e39024",
            "Via3": "#70b512",
        }

        # Needs manual updating
        start_x = min_x + 800
        start_y = -min_y + 350
        spacing = 4000
        box_size = 400

        for i, (metal, color) in enumerate(metal_colors.items()):
            x = start_x + i * spacing

            # Metal name text
            svg_elements.append(
                f'<text x="{x}" y="{start_y + box_size / 2 + 160}" font-size="500" fill="black" alignment-baseline="middle">{metal}</text>')

            # Color box next to the metal name
            box_x = x - 700
            box_y = start_y - 50
            svg_elements.append(
                f'<rect x="{box_x}" y="{box_y}" width="{box_size}" height="{box_size}" fill="{color}" stroke="black" stroke-width="2" />')

        # Needs manual updating
        horizontal_arrow_y_offset = 40300
        horizontal_text_y_offset = 40480
        vertical_arrow_x_offset = 57300
        vertical_text_x_offset = 57480

        length_x = max_x - min_x
        length_y = max_y - min_y

        arrow_defs = """
        <defs>
          <marker id="arrowhead" markerWidth="20" markerHeight="30" 
                  refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,7 L10,3.5 z" fill="black" />
          </marker>

          <marker id="arrowhead_reversed" markerWidth="20" markerHeight="30" 
                  refX="0" refY="3.5" orient="auto" markerUnits="strokeWidth">
            <path d="M10,0 L10,7 L0,3.5 z" fill="black" />
          </marker>
        </defs>
        """

        arrow_elements = [
            # Horizontal arrow line
            f'<line x1="{min_x}" y1="{min_y - horizontal_arrow_y_offset}" x2="{max_x}" '
            f'y2="{min_y - horizontal_arrow_y_offset}" '
            'stroke="black" stroke-width="50" marker-start="url(#arrowhead_reversed)" marker-end="url(#arrowhead)" />',

            # Horizontal length text
            f'<text x="{(min_x + max_x) / 2}" y="{min_y - horizontal_text_y_offset}" '
            f'font-size="500" fill="black" text-anchor="middle">'
            f'{length_x/1000} μm</text>',

            # Vertical arrow line
            f'<line x1="{min_x + vertical_arrow_x_offset}" y1="{min_y}" x2="{min_x + vertical_arrow_x_offset}" '
            f'y2="{-max_y}" '
            'stroke="black" stroke-width="50" marker-start="url(#arrowhead_reversed)" marker-end="url(#arrowhead)" />',

            # Vertical length text (rotated)
            f'<text x="{min_x + vertical_text_x_offset}" y="{-(min_y + max_y) / 2}" '
            f'font-size="500" fill="black" text-anchor="middle" '
            f'transform="rotate(90 {min_x + vertical_text_x_offset},{-(min_y + max_y) / 2})">{length_y/1000} μm</text>'
        ]
        svg_elements.extend(arrow_elements)

        # Custom colors. Needs manual updating
        new_style = """
        <defs>
        <style type="text/css">
          .l70d20 { fill: #1f77b4; fill-opacity: 0.7; }
          .l69d20 { fill: #d62728; fill-opacity: 0.7; }
          .l67d20 { fill: #56423e; fill-opacity: 0.7; }
          .l68d20 { fill: #bea6a1; fill-opacity: 0.7; }
          .l68d44 { fill: #0077ff;}
          .l67d44 { fill: #e09a8e;}
          .l69d44 { fill: #70b512;}
          
          .l50d0 { fill: #1f77b4; fill-opacity: 0.7; } /* Metal 4 in IHP */
          .l49d0{ fill: #70b512;}                      /* Via 3 in IHP */
          .l30d0 { fill: #d62728; fill-opacity: 0.7; } /* Metal 3 in IHP */
          .l29d0 { fill: #e39024;}                     /* Via 2 in IHP */
          .l10d0 { fill: #bea6a1; fill-opacity: 0.7; } /* Metal 2 in IHP */
          .l19d0 { fill: #e09a8e;}                     /* Via 1 in IHP */
          .l8d0 { fill: #56423e; fill-opacity: 0.7; }  /* Metal 1 in IHP */
        
          
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
          .l8d2,
          .l8d25,
          .l30d2,
          .l30d25,
          .l14d0
          .l235d4 {
            fill: #000000;
            fill-opacity: 0.0;
          }
          
          .l998t0 { fill: #000000; font-size: 500px; }
          .l997t0 { fill: #F5F5F5; font-size: 500px;}
          .l999d0 { stroke: #000000; stroke-width: 50; fill: #000000; fill-opacity: 0.2; }
        </style>
        </defs>
        """
        new_style = arrow_defs + new_style

        scale_svg = 0.1
        scaled_min_x = (min_x - pad) * scale_svg
        scaled_min_y = (-max_y - pad) * scale_svg
        scaled_svg_width = svg_width * scale_svg
        scaled_svg_height = svg_height * scale_svg
        svg_body = ' '.join(svg_elements)

        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg"
            width="{scaled_svg_width}" height="{scaled_svg_height}"
            viewBox="{scaled_min_x} {scaled_min_y} {scaled_svg_width} {scaled_svg_height}">
            {new_style}
            <rect x="{scaled_min_x}" y="{scaled_min_y}" width="{scaled_svg_width}" height="{scaled_svg_height}" fill="#ffffff" />
            <g transform="scale({scale_svg})">
              {svg_body}
            </g>
        </svg>
        """

        os.makedirs(os.path.dirname(svg_path), exist_ok=True)
        with open(svg_path, "w") as f:
            f.write(svg_content)


def extract_points(poly):
    # Handles both Polygon and PolygonWithProperties
    base = poly.polygon if hasattr(poly, "polygon") else poly
    return [(pt.x, pt.y) for pt in base.each_point_hull()]
