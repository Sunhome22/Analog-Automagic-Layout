import numpy as np
import matplotlib.pyplot as plt
import math

class CustomPlacement:
    def __init__(self, grid_size, component_size, components_total):
        super(CustomPlacement, self).__init__()
        self.component_positions = None
        self.grid_size = grid_size
        self.component_size = component_size
        self.components_total = components_total
        self.previous_distance = 0
        self.place()

    def plot_placement(self, plot_name):
        # Plot config
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(-self.grid_size, self.grid_size)
        ax.set_ylim(-self.grid_size, self.grid_size)
        ax.set_aspect('equal')
        ax.set_title("Placement", fontsize=16)
        ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

        # Place components
        for i, (x, y) in enumerate(self.component_positions):
            rect = plt.Rectangle((x, y), self.component_size[0], self.component_size[1], edgecolor='green',
                                 facecolor='springgreen')
            ax.add_patch(rect)

            ax.text(x + self.component_size[0] / 2, y + self.component_size[1] / 2, f"{i + 1}",
                    color="black", fontsize=10, ha='center', va='center')

        plt.savefig(plot_name)


    def place(self):
        # Place components at random non-overlapping positions
        self.component_positions = []

        # Place components in 0,0
        #for _ in range(self.components_total):
        #    self.component_positions.append(np.array([0, 0]))
        #self.component_positions = np.array(self.component_positions, dtype=np.int32)

        n = 4
        positions = self.generate_symmetric_grid(n)
        for pos in positions:
            self.component_positions.append(pos)
        self.component_positions = np.array(self.component_positions, dtype=np.int32)

        # Debug
        self.plot_placement(plot_name="custom_placement_algorithm/ok_placement.png")
        print(self.component_positions)


    def generate_symmetric_grid(self, n):
        positions = []

        # Determine the number of rows and columns
        cols = math.ceil(math.sqrt(n))  # Approximate square grid
        rows = math.ceil(n / cols)
        print(rows)
        print(cols)

        y_offset = (rows - 1) / 2

        count = 0
        for row in range(rows):
            for col in range(-(cols // 2), (cols // 2) + 1):  # Symmetric range around 0
                if count >= n:
                    break

                x = col
                y = y_offset - row  # Inverted y to have (0,0) at center

                # Add the point
                positions.append((x, y))
                count += 1

        return positions




