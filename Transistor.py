import matplotlib.pyplot as plt
import matplotlib.patches as patches


def drawNtransistor(ax, x, y, height, width):

    rect = patches.Rectangle((x, y), width, height, fill=True)
    ax.add_patch(rect)

    # Add text labels at various positions
    ax.text(x+width/2, y+height/2, 'N', ha = 'center', va = 'center', fontsize = 20, color = 'blue')
    ax.text(x, y+height/2, 'B', horizontalalignment='left', verticalalignment='center', fontsize=20, color = 'red')
    ax.text(x+width/2, y+height, 'C', horizontalalignment='center', verticalalignment='top', fontsize = 20, color = 'red')
    ax.text(x+width/2,y, 'E', horizontalalignment = 'center', verticalalignment = 'bottom', fontsize=20, color='red')

def drawPtransistor(ax, x, y, height, width):

    rect = patches.Rectangle((x+5, y+5), width, height, fill=True)
    ax.add_patch(rect)
    x+=5
    y+=5
    # Add text labels at various positions
    ax.text(x+width/2, y+height/2, 'P', ha = 'center', va = 'center', fontsize = 20, color = 'blue')
    ax.text(x, y+height/2, 'B', horizontalalignment='left', verticalalignment='center', fontsize=20, color = 'red')
    ax.text(x+width/2, y+height, 'C', horizontalalignment='center', verticalalignment='top', fontsize = 20, color = 'red')
    ax.text(x+width/2,y, 'E', horizontalalignment = 'center', verticalalignment = 'bottom', fontsize=20, color='red')

def main():
    x, width = 1, 3
    y, height = 1, 3
    grid_size = 10

    fix, ax = plt.subplots(figsize=(10, 10))
    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    drawNtransistor(ax, x, y, height, width)
    drawPtransistor(ax, x, y, height, width)


    plt.show()

main()