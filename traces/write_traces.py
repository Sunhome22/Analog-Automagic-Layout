from circuit.circuit_components import Trace, RectAreaLayer, RectArea
from json_tool.json_converter import save_to_json


def segment_path(path):
    if len(path) < 2:
        return []  # No segments for a path with less than 2 points

    segments = []
    current_segment = [path[0]]  # Start with the first point

    # Function to calculate direction between two points
    def direction(p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return (dx, dy)

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

def _rectangle_values(segments):
    rectangles = []

    for seg in segments:
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
        rectangles.append([min_x,max_x,min_y,max_y])

    return rectangles



def write_traces(objects, path, path_names):
    for index, p in enumerate(path):
        print(len(path_names))
        print(len(path))
        a_trace = Trace()
        a_trace.instance = a_trace.__class__.__name__  # add instance type
        a_trace.number_id = index
        a_trace.name = path_names[index]

        segments = segment_path(p)
        rectangles = _rectangle_values(segments)

        for rect in rectangles:

            if rect[0] == rect[1]:
                a_trace.segments.append(RectAreaLayer(layer="m2", area=RectArea(x1=rect[0], y1=rect[2], x2=rect[1], y2=rect[3])))
                #a_trace.vias.append(RectAreaLayer(layer="via1", area=RectArea(x1=300, y1=0, x2=350, y2=50)))
            elif rect[2] == rect[3]:
                a_trace.segments.append(RectAreaLayer(layer="m1", area=RectArea(x1=rect[0], y1=rect[2], x2=rect[1], y2=rect[3])))
       # a_trace.segments.append(RectAreaLayer(layer="m1", area=RectArea(x1=300, y1=0, x2=350, y2=300)))
        objects.append(a_trace)

    save_to_json(objects=objects, file_name="json_tool/test.json")