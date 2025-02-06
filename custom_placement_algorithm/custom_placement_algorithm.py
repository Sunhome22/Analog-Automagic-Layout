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

        n = 8
        m = 1
        positions = self.generate_symmetric_grid(cells=n, groups=m)
        for pos in positions:
            self.component_positions.append(pos)
        self.component_positions = np.array(self.component_positions, dtype=np.float32)

        # Debug
        self.plot_placement(plot_name="custom_placement_algorithm/ok_placement.png")
        print(self.component_positions)

    def generate_symmetric_grid(self, cells, groups):
        positions = []
        cols = math.ceil(math.sqrt(cells))
        rows = math.ceil(cells / cols)


        start_row = 0
        extra_cols = 0
        divider = 2
        divider_2 = 2
        extra_row = 0

        if n % 2 != 0:
            positions.append((-0.5, 0))
            start_row = 1

        if n % 3 != 0:
            extra_row = 1

        if n % 5 == 0 or n % 7 == 0:
            divider = 4

        if n % 6 == 0:
            extra_cols = 1
            extra_row = 1
            divider_2 = 4

        if n % 9 == 0:
            extra_row = 2

        if n % 10 == 0:
            start_row = -1
            divider_2 = 4
            divider = 4


        count = 0
        for row in range(start_row, rows + extra_row):
            for col in range(-cols // divider + extra_cols, cols // divider_2 + extra_cols):
                # prevent extra
                if count >= n:
                    break
                positions.append((col, -row))
                count += 1

        return positions








