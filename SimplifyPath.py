def horizontal_move(p1, p2):
    return p1[1] == p2[1]

def vertical_move(p1, p2):
    return p1[0] == p2[0]

def l_shape(start, end):

    path = []

    for x in range(start[0], end[0]+1 if start[0]<end[0] else end[0]-1, 1 if start[0] < end[0] else-1):
        path.append((x, start[1]))



    for y in range(start[1]+1 if start[1]<end[1] else start[1]-1, end[1], 1 if start[1] < end[1] else-1):
        path.append((end[0], y))
        print(y)
    return path

def simplify_staircase(path):

    if len(path) < 3:
        return path

    simplified_path = []
    i = 0

    while i <len(path) -1:
        start = path[i]
        next_point = path[i+1]
        t = 0

        if i + 2 < len(path) and ((horizontal_move(start, next_point) and vertical_move(next_point, path[i+2]) and horizontal_move(path[i+2], path[i+3])) or (vertical_move(start, next_point) and horizontal_move(next_point, path[i+2]) and vertical_move(path[i+2], path[i+3]))):
            staircase_start = i
            print(f"[INFO] Staircase detected at: {i}")
            if horizontal_move(start, next_point) and vertical_move(next_point, path[i + 2]):
                print("first")
            elif vertical_move(start, next_point) and horizontal_move(next_point, path[i+2]):
                print("Second")

            while i+2 < len(path) and ((horizontal_move(path[i], path[i+1]) and vertical_move(path[i+1], path[i+2])) or (vertical_move(path[i], path[i+1]) and horizontal_move(path[i+1], path[i+2]))):
                i += 2

            staircase_end = i
            print(f"[INFO] Staircase start {staircase_start}")
            print(f"[INFO] Staircase start {staircase_end}")
            l = l_shape(path[staircase_start], path[staircase_end])
            print("[INFO] l shape")
            print(l)

            for p in range(staircase_start,staircase_end):

                path[p] = l[t]
                t+=1

            i = staircase_end
        else:
            simplified_path.append(start)
            i+=1
        if path[-1] != simplified_path[-1]:
            simplified_path.append(path[-1])


    return path

def simplify_all_paths(paths):
    all_simplified_paths = []
    for path in paths:

        all_simplified_paths.append(simplify_staircase(path))


    return all_simplified_paths

def testpath():
    path = [[(2, 27), (3, 27), (4, 27), (5, 27), (6, 27), (7, 27), (8, 27), (9, 27), (10, 27), (11, 27), (12, 27), (13, 27), (14, 27), (15, 27), (16, 27), (17, 27), (18, 27), (19, 27), (19, 26), (20, 26), (20, 25), (21, 25)],
[(2, 27), (3, 27), (4, 27), (5, 27), (6, 27), (7, 27), (8, 27), (9, 27), (10, 27), (11, 27), (12, 27), (13, 27), (14, 27), (15, 27), (16, 27), (17, 27), (18, 27), (19, 27), (19, 26), (20, 26), (20, 25), (21, 25)]
]
    cleaned = simplify_all_paths(path)
    print(cleaned)

    return

testpath()
