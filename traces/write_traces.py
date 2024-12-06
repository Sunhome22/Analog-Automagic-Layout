from dataclasses import dataclass
import re

from dill import objects

from circuit.circuit_components import Trace, RectAreaLayer, RectArea
from json_tool.json_converter import save_to_json
from magic.magic_layout_creator import MagicLayoutCreator

@dataclass
class ComponentLibrary:
    name: str
    path: str


@dataclass
class ProjectProperties:
    directory: str
    name: str
    name_long: str
    component_libraries: list[ComponentLibrary]


# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       name="JNW_BKLE",
                                       name_long="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib, misc_lib])

def direction(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx, dy

def segment_path(path):
    if path is None or len(path) < 2:
        return []  # No segments for a path with less than 2 points

    segments = []
    current_segment = [path[0]]  # Start with the first point
    # Track the initial direction
    current_direction = direction(path[0], path[1])

    for i in range(1, len(path)):
        next_direction = direction(path[i - 1], path[i])
        if next_direction != current_direction:
            # Direction changed, end the current segment
            current_segment.append(path[i - 1])
            segments.append(current_segment)
            # Start a new segment
            current_segment = [path[i - 1]]
            current_direction = next_direction

        # Add the current point to the segment
        current_segment.append(path[i])

    # Add the final segment
    if current_segment:
        segments.append(current_segment)

    return segments

def _rectangle_values(segments,used_area, area_coordinates, path_names, index, port_coord):
    rectangles = []
    name = path_names[index]
    pattern = r"(\d+)([a-zA-Z])-(\d+)([a-zA-Z])"

    # Match the pattern
    match = re.match(pattern, name)

    if match:
        start_id = int(match.group(1))  # First number (4)
        start_port = match.group(2)  # First letter (t)
        end_id = int(match.group(3))  # Second number (17)
        end_port = match.group(4)  # Last letter (j)
    else:
        start_id = 0  # First number (4)
        start_port = 0  # First letter (t)
        end_id = 0  # Second number (17)
        end_port = 0



    for index1, seg in enumerate(segments):

        min_x = seg[0][0]
        max_x = seg[0][0]
        min_y = seg[0][1]
        max_y = seg[0][1]
        for x, y in seg:
            if x>max_x:
                max_x = x
            elif x < min_x:
                min_x = x
            if y> max_y:
              max_y= y
            elif y < min_y:
                min_y = y

        if len(segments == 2):
            if index1 == 0 :
                if min_x == max_x:
                    rectangles.append([port_coord[str(start_id) + start_port][0],port_coord[str(start_id) + start_port][1],port_coord[str(start_id) + start_port][0],port_coord[str(end_id) + end_port][1]])
                elif min_y == max_y:
                    rectangles.append(
                            [port_coord[str(start_id) + start_port][0], port_coord[str(start_id) + start_port][1],
                             port_coord[str(start_id) + start_port][0], port_coord[str(end_id) + end_port][1]])
    return rectangles




def write_traces(objects, path, path_names, used_area, area_coordinates, port_coord):
    trace_width = 32
    for index, p in enumerate(path):

        a_trace = Trace()
        a_trace.instance = a_trace.__class__.__name__  # add instance type
        a_trace.number_id = index
        a_trace.name = path_names[index]

        segments = segment_path(p)
        rectangles = _rectangle_values(segments, used_area, area_coordinates, path_names, index, port_coord)

        for rect in rectangles:

            if rect[0] == rect[2]:
                if rect[1] > rect[3]:
                    a_trace.segments.append(RectAreaLayer(layer="m2", area=RectArea(x1=rect[0]-trace_width//2, y1=rect[1], x2=rect[2]+trace_width//2, y2=rect[3]-trace_width//2)))
                elif rect[1] < rect[3]:
                    a_trace.segments.append(RectAreaLayer(layer="m2",
                                                          area=RectArea(x1=rect[0] - trace_width // 2,
                                                                        y1=rect[1] -  trace_width // 2,
                                                                        x2=rect[2] + trace_width // 2,
                                                                        y2=rect[3]  )))

            elif rect[1] == rect[3]:
                if rect[0] < rect [2]:
                    a_trace.segments.append(RectAreaLayer(layer="m3", area=RectArea(x1=rect[0]-trace_width//2, y1=rect[1]-trace_width//2, x2=rect[2], y2=rect[3]+trace_width//2)))
                elif rect[0] > rect [2]:
                    a_trace.segments.append(RectAreaLayer(layer="m3",
                                                          area=RectArea(x1=rect[0], y1=rect[1] - trace_width//2, x2=rect[2]+trace_width//2,
                                                                        y2=rect[3] + trace_width/2)))
       # a_trace.segments.append(RectAreaLayer(layer="m1", area=RectArea(x1=300, y1=0, x2=350, y2=300)))
        objects.append(a_trace)

    save_to_json(objects=objects, file_name="json_tool/TracesLO1.json")
    # found_stuff = load_from_json(file_name="json_tool/TracesLO1.json")
    MagicLayoutCreator(project_properties=project_properties, components=objects)