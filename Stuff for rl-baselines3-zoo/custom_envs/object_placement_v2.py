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

    def __init__(self, grid_size=10, component_size=(2,2), components_total=4, max_steps=1000):
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

    def reset(self, seed=None, options=None):
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

        # Compute bounding box area
        x_pos = [pos[0] for pos in self.component_positions]
        y_pos = [pos[1] for pos in self.component_positions]
        bounding_box_area = (max(x_pos) - min(x_pos)) * (max(y_pos) - min(y_pos))

        # Check for overlap
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                if self.check_overlap(self.component_positions[i], self.component_positions[j]):
                    overlap_reward -= 100

        # Define reward as minimizing both distance and bounding box area
        distance_reward = 1 / (avg_distance + 1)
        area_reward = 1 / (bounding_box_area + 1)

        # Maybe weight this in the future?
        reward = distance_reward + area_reward + overlap_reward

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



