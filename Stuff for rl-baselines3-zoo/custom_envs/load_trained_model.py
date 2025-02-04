from stable_baselines3 import PPO
import matplotlib.pyplot as plt
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env
import numpy as np
from matplotlib import patches
from object_placement_v2 import ComponentPlacementEnvironment

def plot_placement(grid_size, component_size, component_positions, initial_component_positions, plot_name):
    # Plot config
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    ax.set_aspect('equal')
    ax.set_title("Placement", fontsize=16)
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

    # Place components
    for i, (x, y) in enumerate(component_positions):
        rect = plt.Rectangle((x, y), component_size[0], component_size[1], edgecolor='green', facecolor='springgreen')
        ax.add_patch(rect)

        ax.text(x + component_size[0] / 2, y + component_size[1] / 2, f"{i + 1}",
                color="black", fontsize=10, ha='center', va='center')

    for i, (x, y) in enumerate(initial_component_positions):
        init_rect = plt.Rectangle((x, y), component_size[0], component_size[1], edgecolor='red', facecolor='lightcoral')
        ax.add_patch(init_rect)

        ax.text(x + component_size[0] / 2, y + component_size[1] / 2, f"{i + 1} initial",
                color="black", fontsize=10, ha='center', va='center')

    plt.savefig(plot_name)

def load_trained_model():
    max_steps = 1000
    grid_size = 10
    component_size = (2, 2)  # (576, 400)
    components_total = 4

    env = make_vec_env(ComponentPlacementEnvironment, n_envs=3,
                               env_kwargs=dict(grid_size=grid_size, component_size=component_size,
                                               components_total=components_total, max_steps=max_steps))


    trained_model = PPO.load(f"/pri/bjs1/Analog-Automagic-Layout/rl-baselines3-zoo/logs/ppo/ComponentPlacementEnvironment-v2_9/best_model", env=env)

    next_placements = env.reset()
    initial_placements = next_placements
    placements = []

    while True:
        action, _states = trained_model.predict(next_placements, deterministic=False)
        next_placements, reward, completed, truncated = env.step(action)
        # print(next_placements)
        if completed.any():
            break

        placements = next_placements  # A hack to deal with SB3s auto reset when done = True

    env.close()

    print(f"Placement positions: {placements}")
    print(f"Initial Observation: {initial_placements}")
    plot_placement(grid_size=grid_size, component_size=component_size, component_positions=placements[0],
                   initial_component_positions=initial_placements[0], plot_name="placement_test_1")

    plot_placement(grid_size=grid_size, component_size=component_size, component_positions=placements[1],
                   initial_component_positions=initial_placements[1], plot_name="placement_test_2")

    plot_placement(grid_size=grid_size, component_size=component_size, component_positions=placements[2],
                   initial_component_positions=initial_placements[2], plot_name="placement_test_3")

    # tensorboard --logdir=ml_exploration/logs --bind_all

if __name__ == '__main__':
    load_trained_model()