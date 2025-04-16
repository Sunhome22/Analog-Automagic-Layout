import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import csv
def visualize_grid(grid):


    # Example nested list (grid)

    data = np.array(grid)

    fig, ax = plt.subplots()

    # Display the data with a chosen colormap
    cax = ax.matshow(data, cmap='viridis')

    # Annotate each cell with its value
    for (i, j), val in np.ndenumerate(data):
        ax.text(j, i, f'{val}', ha='center', va='center', color='white', fontsize=12)

    # Set ticks for each cell
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))

    # Optional: add grid lines
    ax.set_xticks(np.arange(-.5, data.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-.5, data.shape[0], 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    plt.title("Enhanced Grid Visualization")
    plt.colorbar(cax)
    plt.show()

def heatmap_test(grid, name):



    # Example grid (120x60)

    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(grid, cmap='coolwarm', cbar=True, linewidths=0.5)
    ax.invert_yaxis()
    plt.title("120x60 Grid Visualization")
    plt.savefig('src/results/'+name+'.png')

def save_matrix(matrix, filename):
    with open(filename + '.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(matrix)
    return

def load_matrix(filename):
# Load the matrix from the file
    loaded_matrix = []
    with open(filename+'.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            loaded_matrix.append([int(element) for element in row])
    return loaded_matrix