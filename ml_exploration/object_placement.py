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

 # This is some kind of begining. Now i need to understand what is happening here


# Define your environment class (already done in previous sections)
class ChipFloorplanningEnv(gym.Env):
    def __init__(self, grid_size=3000, chip_size=(567, 400), num_chips=4, max_steps=1000):
        super(ChipFloorplanningEnv, self).__init__()
        self.grid_size = grid_size
        self.chip_size = chip_size
        self.num_chips = num_chips
        self.max_steps = max_steps

        # State: Chip positions on the grid (x, y) for each chip
        self.observation_space = gym.spaces.Box(
            low=0,
            high=grid_size - max(chip_size),  # Ensure chips stay within the grid
            shape=(num_chips, 2),
            dtype=np.int32,
        )

        # Action: Move a chip (chip_index, dx, dy)
        self.action_space = gym.spaces.MultiDiscrete(
            [num_chips, 3, 3]  # [chip_index, dx (-1, 0, 1), dy (-1, 0, 1)]
        )

        self.reset()

    def reset(self, seed=None):
        # Accept the seed argument
        self.np_random, _ = gym.utils.seeding.np_random(seed)

        # Initialize chips at random non-overlapping positions
        self.chip_positions = []
        for _ in range(self.num_chips):
            while True:
                # Use integers() instead of randint() for the random number generation
                x = self.np_random.integers(0, self.grid_size - self.chip_size[0])
                y = self.np_random.integers(0, self.grid_size - self.chip_size[1])
                new_position = np.array([x, y])
                if not any(self.check_overlap(new_position, pos) for pos in self.chip_positions):
                    self.chip_positions.append(new_position)
                    break
        self.chip_positions = np.array(self.chip_positions, dtype=np.int32)
        self.steps = 0

        # Return observation and info (info can be empty for now)
        return self.chip_positions, {}

    def step(self, action):
        chip_index, dx, dy = action
        dx *= 10  # Scale movement for better granularity
        dy *= 10

        # Update the position of the selected chip
        self.chip_positions[chip_index, 0] = np.clip(
            self.chip_positions[chip_index, 0] + dx, 0, self.grid_size - self.chip_size[0]
        )
        self.chip_positions[chip_index, 1] = np.clip(
            self.chip_positions[chip_index, 1] + dy, 0, self.grid_size - self.chip_size[1]
        )

        # Compute the reward
        reward = self.compute_reward()

        # Increment steps and check if the episode is done
        self.steps += 1
        done = self.steps >= self.max_steps

        # Truncate if necessary
        truncated = False  # You can set this based on your specific requirements

        # Return 5 values: observation, reward, done, truncated, and info
        return self.chip_positions, reward, done, truncated, {}

    def compute_reward(self):
        reward = 0

        # Penalize overlaps
        for i in range(self.num_chips):
            for j in range(i + 1, self.num_chips):
                if self.check_overlap(self.chip_positions[i], self.chip_positions[j]):
                    reward -= 20  # Stronger penalty for overlap

        # Minimize distance between all chips (example heuristic)
        for i in range(self.num_chips):
            for j in range(i + 1, self.num_chips):
                dist = np.linalg.norm(self.chip_positions[i] - self.chip_positions[j])
                reward -= dist / 500  # Normalize to keep the reward in a reasonable range

        return reward

    def check_overlap(self, pos1, pos2):
        # Check if two chips overlap
        x1, y1 = pos1
        x2, y2 = pos2
        return not (
            x1 + self.chip_size[0] <= x2
            or x2 + self.chip_size[0] <= x1
            or y1 + self.chip_size[1] <= y2
            or y2 + self.chip_size[1] <= y1
        )


def plot_chip_placement(grid_size, chip_size, chip_positions):
    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw the grid boundary
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    ax.set_aspect('equal')
    ax.set_title("Chip Floorplanning Result", fontsize=16)
    ax.set_xlabel("X-axis", fontsize=12)
    ax.set_ylabel("Y-axis", fontsize=12)
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
            f"Transistor {i + 1}",
            color="black", fontsize=10, ha='center', va='center'
        )

    # Show the plot
    plt.savefig("shit_placement.png")


def object_placement():
    env = DummyVecEnv([lambda: ChipFloorplanningEnv()])

    # Initialize PPO agent
    model = PPO("MlpPolicy", env, verbose=1, device="cpu")

    # Train the agent
    model.learn(total_timesteps=100000)  # Adjust the number of timesteps based on your use case

    # Save the trained model
    model.save("ppo_chip_floorplanning")

    # Optionally, load the trained model to evaluate or use later
    obs = env.reset()  # Reset the environment to get the initial observation
    done = False

    print("Initial Observation:", obs)  # Debugging line

    for step in range(1000):
        action, _states = model.predict(obs, deterministic=True)
        print("Action:", action)  # Debugging line
        obs, reward, done, truncated = env.step(action)
        if done:
            break

    print("Final Chip Positions:")
    print(obs)

    original_env = env.unwrapped
    plot_chip_placement(original_env.grid_size, original_env.chip_size, obs)