from dataclasses import dataclass
import re



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


def _calc_tmp_endpoint(x1, x2, l):
    tot = l[0] + l[-1]

    if x2 > x1:

        weight = round((x2 - x1) * (l[0] / tot))
    else:
        weight = round((x1 - x2) * (l[0] / tot))

    return weight


def _rectangle_values(segments, used_area, area_coordinates, path_names, index, port_coord):
    rectangles = []
    lengths = []
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

    temp_end_point_x = 0
    temp_end_point_y = 0

    for s in segments:
        lengths.append(len(s))

    for index1, seg in enumerate(segments):

        min_x = seg[0][0]
        max_x = seg[0][0]
        min_y = seg[0][1]
        max_y = seg[0][1]
        for x, y in seg:
            if x > max_x:
                max_x = x
            elif x < min_x:
                min_x = x
            if y > max_y:
                max_y = y
            elif y < min_y:
                min_y = y

        if len(segments) == 1:
            if min_x == max_x:
                rectangles.append(
                    [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                     port_coord[str(start_id) + start_port][0][0], port_coord[str(end_id) + end_port][0][1]])
            else:
                rectangles.append(
                    [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                     port_coord[str(end_id) + end_port][0][0], port_coord[str(start_id) + start_port][0][1]])


        elif len(segments) == 2:
            if index1 == 0:
                if min_x == max_x:
                    print("we end up here")
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                         port_coord[str(start_id) + start_port][0][0], port_coord[str(end_id) + end_port][0][1]])
                else:
                    print("we end up here")
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                         port_coord[str(end_id) + end_port][0][0], port_coord[str(start_id) + start_port][0][1]])
            elif index1 == 1:
                if min_x == max_x:
                    rectangles.append(
                        [port_coord[str(end_id) + end_port][0][0], port_coord[str(start_id) + start_port][0][1],
                         port_coord[str(end_id) + end_port][0][0], port_coord[str(end_id) + end_port][0][1]])
                else:
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], port_coord[str(end_id) + end_port][0][1],
                         port_coord[str(end_id) + end_port][0][0], port_coord[str(end_id) + end_port][0][1]])

        elif len(segments) == 3:

            if index1 == 0:
                if min_x == max_x:
                    temp_end_point_y = _calc_tmp_endpoint(port_coord[str(start_id) + start_port][0][1],
                                                          port_coord[str(end_id) + end_port][0][1], lengths)
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                         port_coord[str(start_id) + start_port][0][0], temp_end_point_y])
                else:
                    temp_end_point_x = _calc_tmp_endpoint(port_coord[str(start_id) + start_port][0][0],
                                                          port_coord[str(end_id) + end_port][0][0], lengths)
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], port_coord[str(start_id) + start_port][0][1],
                         temp_end_point_x, port_coord[str(start_id) + start_port][0][1]])
            elif index1 == 1:
                if min_x == max_x:
                    rectangles.append([temp_end_point_x, port_coord[str(start_id) + start_port][0][1], temp_end_point_x,
                                       port_coord[str(end_id) + end_port][0][1]])
                else:
                    rectangles.append(
                        [port_coord[str(start_id) + start_port][0][0], temp_end_point_y,
                         port_coord[str(end_id) + end_port][0][0], temp_end_point_y])
            elif index1 == 2:
                if min_x == max_x:
                    rectangles.append([port_coord[str(end_id) + end_port][0][0], temp_end_point_y,
                                       port_coord[str(end_id) + end_port][0][0],
                                       port_coord[str(end_id) + end_port][0][1]])
                else:
                    rectangles.append(
                        [temp_end_point_x, port_coord[str(end_id) + end_port][0][1],
                         port_coord[str(end_id) + end_port][0][0], port_coord[str(end_id) + end_port][0][1]])

    return rectangles


def write_traces(objects, path, path_names, used_area, area_coordinates, port_coord):
    trace_width = 32
    for index, p in enumerate(path):
        print(index)
        a_trace = Trace()
        a_trace.instance = a_trace.__class__.__name__  # add instance type
        a_trace.number_id = index
        a_trace.name = path_names[index]

        segments = segment_path(p)
        rectangles = _rectangle_values(segments, used_area, area_coordinates, path_names, index, port_coord)

        for rect in rectangles:
            print("rectangl")
            print(rect)
            if rect[0] == rect[2]:
                if rect[1] > rect[3]:
                    a_trace.segments.append(RectAreaLayer(layer="m2",
                                                          area=RectArea(x1=rect[0] - trace_width // 2, y1=rect[3]- trace_width // 2,
                                                                        x2=rect[2] + trace_width // 2,
                                                                        y2=rect[1]+ trace_width // 2 )))
                elif rect[1] < rect[3]:
                    a_trace.segments.append(RectAreaLayer(layer="m2",
                                                          area=RectArea(x1=rect[0] - trace_width // 2,
                                                                        y1=rect[1]- trace_width // 2 ,
                                                                        x2=rect[2] + trace_width // 2,
                                                                        y2=rect[3]+ trace_width // 2)))

            elif rect[1] == rect[3]:
                if rect[0] < rect[2]:
                    a_trace.segments.append(RectAreaLayer(layer="m3", area=RectArea(x1=rect[0]- trace_width // 2,
                                                                                    y1=rect[1] - trace_width // 2,
                                                                                    x2=rect[2]+ trace_width // 2,
                                                                                    y2=rect[3] + trace_width // 2)))
                elif rect[0] > rect[2]:
                    a_trace.segments.append(RectAreaLayer(layer="m3",
                                                          area=RectArea(x1=rect[2]- trace_width // 2, y1=rect[1] - trace_width // 2,
                                                                        x2=rect[0]+ trace_width // 2 ,
                                                                        y2=rect[3] + trace_width // 2)))
        # a_trace.segments.append(RectAreaLayer(layer="m1", area=RectArea(x1=300, y1=0, x2=350, y2=300)))

        print(f"a_trace: {a_trace}")
        objects.append(a_trace)

    save_to_json(objects=objects, file_name="json_tool/TracesLO1.json")
    # found_stuff = load_from_json(file_name="json_tool/TracesLO1.json")
    MagicLayoutCreator(project_properties=project_properties, components=objects)