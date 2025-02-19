from curses.textpad import rectangle

import numpy as np
import matplotlib.pyplot as plt
class Nets:
    applicable_nets:list
    pin_nets: list

    def __init__(self, applicable_nets: list, pin_nets:list):
        self.applicable_nets = applicable_nets
        self.pin_nets = pin_nets

def main():
    grid = [
        [0, 1, 0, 1],
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [1, 0, 1, 0]
    ]

    # Convert the nested list into a NumPy array
    data = np.array(grid)

    # Display the grid as an image
    plt.imshow(data, cmap='viridis', interpolation='nearest')
    plt.colorbar()  # Optional: adds a color bar legend
    plt.title("Grid Visualization")
    plt.show()



if __name__ == '__main__':
    main()



