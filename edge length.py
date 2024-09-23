from Main import connections

def manhattan_distance( obj1, obj2):

    return abs(obj1[0] - obj2[0]) + abs(obj1[1] - obj2[1])


def total_edge_length(objects, connections):
    #Calculate the total edge length (L) as the sum of Manhattan distances between connected objects."""
    total_length = 0
    for a, b in connections:
        total_length += manhattan_distance(objects[a], objects[b])
        (print(total_length))
    return total_length


def main():

    objects = [(1, 1), (2, 1), (4,2), (6,7)]

    connections = ((0,1), (2,3))

    l = total_edge_length(objects, connections)

    print(f"total edge length: {l}")


main()