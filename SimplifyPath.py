def horizontal_move(p1, p2):
    return p1[1] == p2[1]

def vertical_move(p1, p2):
    return p1[0] == p2[0]

def l_shape(start, end):

    path = []

    for x in range(start[0], end[0]+1 if start[0]<end[0] else end[0]-1, 1 if start[0] < end[0] else-1):
        path.append((x, start[1]))


    for y in range(start[1]+1, end[1]+1 if start[0]<end[0] else end[1]-1, 1 if start[1] < end[1] else-1):
        path.append((end[0], y))
    return path

def simplify_staircase(path):

    if len(path) < 3:
        return path

    simplified_path = []
    i = 0

    while i <len(path) -1:
        start = path[i]
        next_point = path[i+1]


        if i + 2 < len(path) and ((horizontal_move(start, next_point) and vertical_move(next_point, path[i+2])) or (vertical_move(start, next_point) and horizontal_move(next_point, path[i+2]))):
            staircase_start = i
            while i+2 < len(path) and ((horizontal_move(path[i], path[i+1]) and vertical_move(path[i+1], path[i+2])) or (vertical_move(path[i], path[i+1]) and horizontal_move(path[i+1], path[i+2]))):
                i += 2

            staircase_end = i
            l = l_shape(path[staircase_start], path[staircase_end])

            simplified_path.extend(l)
            i = staircase_end
        else:
            simplified_path.append(start)
            i+=1

        simplified_path.append(path[-1])
    return simplified_path

def simplify_all_paths(paths):
    all_simplified_paths = []
    for path in paths:
        all_simplified_paths.append(simplify_staircase(path))

    return all_simplified_paths