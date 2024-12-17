import re
from dataclasses import dataclass
import re
import math


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
    cell_name: str
    lib_name: str
    component_libraries: list[ComponentLibrary]


# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       cell_name="JNW_BKLE",
                                       lib_name="JNW_BKLE_SKY130A",
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
def calculate_segment_length(segment):
    return sum(
        math.sqrt((segment[i][0] - segment[i - 1][0])**2 + (segment[i][1] - segment[i - 1][1])**2)
        for i in range(1, len(segment))
    )

def _calc_tmp_endpoint(start, end, lengths, segment_index, total_length):

    if total_length == 0:
        return start  # Avoid division by zero if all lengths are zero

    cumulative_length = sum(lengths[:segment_index])
    ratio = cumulative_length / total_length
    return start + (end - start) * ratio

def calculate_directional_lengths(path_segments):

    length_x = 0
    length_y = 0

    for segment in path_segments:
        if segment[0][0] == segment[-1][0]:  # Vertical segment
            length_y += abs(segment[-1][1] - segment[0][1])  # Vertical length
        elif segment[0][1] == segment[-1][1]:  # Horizontal segment
            length_x += abs(segment[-1][0] - segment[0][0])  # Horizontal length
        else:
            raise ValueError("Segments must be either horizontal or vertical.")
    if length_x == 0:
        length_x = 1

    if length_y == 0:
        length_y = 1
    return length_x, length_y


def map_path_to_rectangles(path_segments, port_coord, path_name):
    rectangles = []
    length_x, length_y = calculate_directional_lengths(path_segments)

    pattern = r"(\d+)([a-zA-Z])-(\d+)([a-zA-Z])"
    match = re.match(pattern, path_name)

    if match:
        start_id = int(match.group(1))
        start_port = match.group(2)
        end_id = int(match.group(3))
        end_port = match.group(4)
    else:
        print("[ERROR]: Invalid path name, pattern not found")

    # Get the real-world start and end coordinates
    start_real = port_coord[f"{start_id}{start_port}"][0]
    end_real = port_coord[f"{end_id}{end_port}"][0]

    cumulative_x = 0
    cumulative_y = 0



    for segment in path_segments:
        start_x, start_y = start_real if not rectangles else (rectangles[-1][2], rectangles[-1][3])

        if segment[0][0] == segment[-1][0]:  # Vertical segment
            segment_length = abs(segment[-1][1] - segment[0][1])
            cumulative_y += segment_length
            end_x = start_x
            if end_real[1] > start_real[1]:
                end_y = start_real[1] + (end_real[1] - start_real[1]) * (cumulative_y / length_y)
            else:
                end_y = start_real[1] - (start_real[1]- end_real[1]) * (cumulative_y / length_y)
        elif segment[0][1] == segment[-1][1]:  # Horizontal segment
            segment_length = abs(segment[-1][0] - segment[0][0])
            cumulative_x += segment_length
            end_y = start_y
            if end_real[0] > start_real[0]:
                end_x = start_real[0] + (end_real[0] - start_real[0]) * (cumulative_x / length_x)
            else:
                end_x = start_real[0] - (start_real[0]- end_real[0]) * (cumulative_x / length_x)

        else:
            print("ERROR: Invalid segment, must be either vertical or horizontal")

        rectangles.append([start_x, start_y, end_x, end_y])

    return rectangles



def write_traces(objects, path, path_names,  port_coord):
    trace_width = 30
    for index, p in enumerate(path):
        a_trace = Trace()
        a_trace.instance = a_trace.__class__.__name__  # Add instance type
        a_trace.number_id = index
        a_trace.name = path_names[index]

        segments = segment_path(p)
        if len(segments) > 0:
            rectangles = map_path_to_rectangles(segments, port_coord, path_names[index])

            for rect in rectangles:
                if rect[0] == rect[2]:  # Vertical
                    if rect[1] > rect[3]:  # Ensure y1 < y2
                        rect[1], rect[3] = rect[3], rect[1]
                    a_trace.segments.append(RectAreaLayer(
                        layer="m2",
                        area=RectArea(
                            x1=int(rect[0]) - trace_width // 2, #Adding width to trace
                            y1=int(rect[1]),
                            x2=int(rect[2]) + trace_width // 2,
                            y2=int(rect[3])
                        )
                    ))
                elif rect[1] == rect[3]:  # Horizontal
                    if rect[0] > rect[2]:  # Ensure x1 < x2
                        rect[0], rect[2] = rect[2], rect[0]
                    a_trace.segments.append(RectAreaLayer(
                        layer="m3",
                        area=RectArea(
                            x1=int(rect[0]),
                            y1=int(rect[1]) - trace_width // 2,
                            x2=int(rect[2]),
                            y2=int(rect[3]) + trace_width // 2
                        )
                    ))


            objects.append(a_trace)

    save_to_json(objects=objects, file_name="json_tool/TracesLO1.json")
    # found_stuff = load_from_json(file_name="json_tool/TracesLO1.json")
    MagicLayoutCreator(project_properties=project_properties, components=objects)