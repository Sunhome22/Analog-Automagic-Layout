import matplotlib.pyplot as plt
import numpy as np

def plot_array_with_extra_points_and_curve(arr, extra_xs, extra_ys, filename='plot.png', poly_order=2):
    # Prepare the data
    x = list(range(1, len(arr) + 1))
    y = arr

    # Combine main and extra points for fitting
    all_x = np.array(x + list(extra_xs))
    all_y = np.array(list(y) + list(extra_ys))

    # Fit polynomial to the combined points
    coeffs = np.polyfit(all_x, all_y, poly_order)
    poly = np.poly1d(coeffs)

    # For smooth curve, make continuous x values
    x_curve = np.linspace(min(all_x), max(all_x), 500)
    y_curve = poly(x_curve)

    # Plotting
    plt.plot(x, y, marker='o', linestyle='-', label='Array Data')
    plt.scatter(extra_xs, extra_ys, color='red', label='Extra Points', zorder=5)
    plt.plot(x_curve, y_curve, color='green', linestyle='--', label=f'Poly{poly_order} Fit')

    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.title('Array Plot with Extra Points and Fitted Curve')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# Example usage:
sample_array = [8, 23, 41, 66, 94, 129, 167, 212, 260, 315, 373, 438, 506, 581, 659, 744, 832, 927, 1025, 1130, 1238, 1353, 1471, 1596, 1724, 1859, 1997, 2142, 2290, 2443, 2603, 2768, 2936, 3111, 3289, 3474, 3662, 3857, 4055, 4260
]
extra_xs = [79, 200]     # x-coordinates of extra points
extra_ys = [16115, 101300]    # y-coordinates of extra points
plot_array_with_extra_points_and_curve(sample_array, extra_xs, extra_ys, 'curve_estimate.png', poly_order=2)