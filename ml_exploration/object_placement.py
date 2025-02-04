from curses.textpad import rectangle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
import pandas as pd
from sklearn.model_selection import train_test_split
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.env_util import make_vec_env
from functools import lru_cache
import os
from datetime import datetime
import math


class ComponentPlacementEnvironment(gym.Env):
    """Utilizes Stable-Baselines3 with its skeleton functions to create a reinforcement learning environment"""

    def __init__(self, grid_size, component_size, components_total, max_steps):
        super(ComponentPlacementEnvironment, self).__init__()

        self.component_positions = None
        self.np_random = None
        self.steps = None

        self.grid_size = grid_size
        self.component_size = component_size
        self.components_total = components_total
        self.max_steps = max_steps
        self.previous_distance = 0

        # Observation and action spaces
        self.observation_space = gym.spaces.Box(
            low=0,
            high=grid_size - max(component_size),
            shape=(components_total, 2),  # 2D array of components
            dtype=np.int32,
        )
        self.action_space = gym.spaces.MultiDiscrete(
            [components_total, 3, 3]  # component_index, dx (-1, 0, 1), dy (-1, 0, 1)
        )
        self.reset()

    def reset(self, seed=None):
        super().reset(seed=seed)
        self.np_random, _ = gym.utils.seeding.np_random(seed)

        # Place components at random non-overlapping positions
        self.component_positions = []

        for _ in range(self.components_total):
            while True:
                x = self.np_random.integers(0, self.grid_size - self.component_size[0])
                y = self.np_random.integers(0, self.grid_size - self.component_size[1])
                new_position = np.array([x, y])

                if not any(self.check_overlap(new_position, pos) for pos in self.component_positions):
                    self.component_positions.append(new_position)
                    break

        self.component_positions = np.array(self.component_positions, dtype=np.int32)
        self.steps = 0

        return self.component_positions, {}

    def step(self, action):
        component_index, dx, dy = action
        dx -= 1  # shift to (-1, 0, 1)
        dy -= 1  # shift to (-1, 0, 1)

        # Update position of the selected component
        self.component_positions[component_index, 0] = np.clip(
            self.component_positions[component_index, 0] + dx, 0, self.grid_size - self.component_size[0]
        )
        self.component_positions[component_index, 1] = np.clip(
            self.component_positions[component_index, 1] + dy, 0, self.grid_size - self.component_size[1]
        )

        reward = self.reward()

        # print(f"id: {component_index}, dx: {dx}, dy: {dy}")
        # print(f"x: {self.component_positions[component_index, 0]}, y: {self.component_positions[component_index, 1]}")
        # print(f"reward: {reward}")
        # print(f"positions: {self.component_positions}")

        self.steps += 1
        done = self.steps >= self.max_steps - 1

        # Unused
        truncated = False
        info = {}

        return self.component_positions, reward, done, truncated, info

    def reward(self):
        total_distance = 0
        overlap_reward = 0
        # Compute pairwise distances
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                total_distance += np.linalg.norm(self.component_positions[i] - self.component_positions[j])

        # Normalized distances
        avg_distance = total_distance / self.get_number_of_pairs(self.components_total)

        # print(f"total_distance {total_distance}")
        # print(f"avg_distance {avg_distance}")

        # Compute bounding box area
        x_pos = [pos[0] for pos in self.component_positions]
        y_coords = [pos[1] for pos in self.component_positions]
        bounding_box_area = (max(x_pos) - min(x_pos)) * (max(y_coords) - min(y_coords))

        # Check for overlap
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                if self.check_overlap(self.component_positions[i], self.component_positions[j]):
                    overlap_reward -= 1

        # Define reward as minimizing both distance and bounding box area
        distance_reward = 1 / (avg_distance + 1)
        area_reward = 1 / (bounding_box_area + 1)

        # Maybe weight this in the future?

        reward = distance_reward + area_reward + overlap_reward

        # print(f"distance avg. : {avg_distance}")
        print(f"distance reward: {distance_reward}")
        # print(f"area penalty: {area_reward}")
        print(f"overlap reward: {overlap_reward}")
        print(f"reward total: {reward}")

        return reward

    @lru_cache(maxsize=None)
    def get_number_of_pairs(self, n):
        return max(1, n * (n - 1) / 2)

    def check_overlap(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2

        return not (
                x1 + self.component_size[0] <= x2
                or x2 + self.component_size[0] <= x1
                or y1 + self.component_size[1] <= y2
                or y2 + self.component_size[1] <= y1
        )


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


def lr_schedule(progress_remaining):
    initial_lr = 1e-3  # Start rate
    final_lr = 1e-4  # Minimum rate
    decay_rate = 1.1

    # Exponentially decayed learning rate
    return final_lr + (initial_lr - final_lr) * math.exp(-decay_rate * (1 - progress_remaining))


def object_placement():
    max_steps = 10000
    grid_size = 10
    component_size = (2, 2)  # (576, 400)
    components_total = 4
    time_steps = 10000
    train = True

    models_dir = f"ml_exploration/models/PPO-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    log_dir = f"ml_exploration/logs/PPO-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    env = make_vec_env(ComponentPlacementEnvironment, n_envs=2,
                               env_kwargs=dict(grid_size=grid_size, component_size=component_size,
                                               components_total=components_total, max_steps=max_steps))

    model = PPO("MlpPolicy", env, verbose=1, device="cpu", tensorboard_log=log_dir, learning_rate=1e-3)

    if train:
        # Folder structure
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        for i in range(1, 101):
            model.learn(total_timesteps=time_steps, reset_num_timesteps=False, tb_log_name="PPO")
            model.save(f"{models_dir}/{time_steps*i}")

    #
    # ml_exploration/models/PPO-2025-02-03_11-45-47/200000
    trained_model = PPO.load(f"{models_dir}/1000000", env=env)

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

    # tensorboard --logdir=ml_exploration/logs --bind_all
