from curses.textpad import rectangle

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
import pandas as pd
from sklearn.model_selection import train_test_split

import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv


class ComponentPlacementEnv(gym.Env):
    def __init__(self, grid_size=3000, component_size=(576, 400), components_total=4, max_steps=1000):
        super(ComponentPlacementEnv, self).__init__()
        self.component_positions = None
        self.np_random = None
        self.steps = None

        self.grid_size = grid_size
        self.chip_size = component_size
        self.components_total = components_total
        self.max_steps = max_steps

        # Spaces
        self.observation_space = gym.spaces.Box(
            low=0,
            high=grid_size - max(component_size),  # Ensure component stays within the grid
            shape=(components_total, 2),
            dtype=np.int32,
        )
        self.action_space = gym.spaces.MultiDiscrete(
            [components_total, 3, 3]  # [component_index, dx (-1, 0, 1), dy (-1, 0, 1)]
        )

        self.reset(seed=None)

    def reset(self, seed=None):
        self.np_random, _ = gym.utils.seeding.np_random(seed)  # random seed

        # Place components at random non-overlapping positions
        self.component_positions = []

        for _ in range(self.components_total):
            while True:
                x = self.np_random.integers(0, self.grid_size - self.chip_size[0])
                y = self.np_random.integers(0, self.grid_size - self.chip_size[1])
                new_position = np.array([x, y])

                if not any(self.check_overlap(new_position, pos) for pos in self.component_positions):
                    self.component_positions.append(new_position)
                    break

        self.component_positions = np.array(self.component_positions, dtype=np.int32)
        self.steps = 0

        return self.component_positions, {}

    def step(self, action):
        component_index, dx, dy = action
        dx *= 10
        dy *= 10

        # Update the position of the selected components
        self.component_positions[component_index, 0] = np.clip(
            self.component_positions[component_index, 0] + dx, 0, self.grid_size - self.chip_size[0]
        )
        self.component_positions[component_index, 1] = np.clip(
            self.component_positions[component_index, 1] + dy, 0, self.grid_size - self.chip_size[1]
        )

        reward = self.reward()
        self.steps += 1
        done = self.steps >= self.max_steps

        # Truncate if necessary
        truncated = False

        return self.component_positions, reward, done, truncated, {}

    def reward(self):
        reward = 0

        # Overlaps are bad for now
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                if self.check_overlap(self.component_positions[i], self.component_positions[j]):
                    reward -= 2  # Stronger penalty for overlap

        # Minimize distance between all components
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                dist = np.linalg.norm(self.component_positions[i] - self.component_positions[j])

                reward -= dist / 500

        return reward

    def check_overlap(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2

        return not (
            x1 + self.chip_size[0] <= x2
            or x2 + self.chip_size[0] <= x1
            or y1 + self.chip_size[1] <= y2
            or y2 + self.chip_size[1] <= y1
        )


def plot_placement(grid_size, chip_size, chip_positions):
    if len(chip_positions.shape) == 3:
        chip_positions = chip_positions[0]

    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw the grid boundary
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    ax.set_aspect('equal')
    ax.set_title("Shit placement", fontsize=16)
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

    # Draw the chips
    for i, (x, y) in enumerate(chip_positions):
        rect = plt.Rectangle(
            (x, y), chip_size[0], chip_size[1],
            edgecolor='blue', facecolor='lightblue', alpha=0.7
        )
        ax.add_patch(rect)
        # Label the chips
        ax.text(
            x + chip_size[0] / 2, y + chip_size[1] / 2,
            f"Component {i + 1}",
            color="black", fontsize=10, ha='center', va='center'
        )

    # Show the plot
    plt.savefig("shit_placement.png")


def object_placement():
    env = DummyVecEnv([lambda: ComponentPlacementEnv()])

    model = PPO("MlpPolicy", env, verbose=1, device="cpu")
    #model.learn(total_timesteps=100000)
    #model.save("ppo_model")

    model.load("ppo_model")
    observation = env.reset()  # Reset the environment to get the initial observation
    initial_observation = observation
    done = False

    for step in range(1000):
        action, _states = model.predict(observation, deterministic=True)
        print("Action:", action)  # Debugging line
        observation, reward, done, truncated = env.step(action)
        print(reward)
        if done:
            break

    print(f"Placement positions: {observation}")
    print(f"Initial Observation: {initial_observation}")  # Debugging line
    plot_placement(3000, (576, 400),observation)