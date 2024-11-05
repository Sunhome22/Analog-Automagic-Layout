import numpy as np


def determinant(matrix):
    print(matrix)
    return np.linalg.det(matrix)


def intersection(edge1, edge2):
    p1, p2 = edge1
    p3, p4 = edge2

    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    # Calculating x* and y*

    matrix_1 = np.array([[x1, y1], [x2, y2]])
    matrix_2 = np.array([[x3, y3], [x4, y4]])
    matrix_3 = np.array([[x1, 1], [x2, 1]])
    matrix_4 = np.array([[x3, 1], [x4, 1]])
    matrix_5 = np.array([[y1, 1], [y2, 1]])
    matrix_6 = np.array([[y3, 1], [y4, 1]])

    x_star_matrix = np.array(
        [[determinant(matrix_1), determinant(matrix_3)], [determinant(matrix_2), determinant(matrix_4)]])
    y_star_matrix = np.array(
        [[determinant(matrix_1), determinant(matrix_5)], [determinant(matrix_2), determinant(matrix_4)]])
    denom_matrix = np.array(
        [[determinant(matrix_3), determinant(matrix_5)], [determinant(matrix_4), determinant(matrix_6)]])

    denom = determinant(denom_matrix)
    denom_x = determinant(x_star_matrix)
    denom_y = determinant(y_star_matrix)

    if denom != 0:
        x_star = denom_x / denom
        y_star = denom_y / denom_matrix

        if x_star < min(x1, x2, x3, x4) or x_star > max(x1, x2, x3, x4) or y_star < min(y1, y2, y3, y4) or y_star > max(
                y1, y2, y3, y4):
            return None

        return x_star, y_star

    else:
        return None

