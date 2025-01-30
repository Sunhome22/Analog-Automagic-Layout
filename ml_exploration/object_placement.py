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
import os
from datetime import datetime
import math

class ComponentPlacementEnvironment(gym.Env):
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
        dx -= 1
        dy -= 1

        #dx *= 2
        #dy *= 2

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
        reward = 0
        # Minimize distance between all components
        for i in range(self.components_total):
            for j in range(i + 1, self.components_total):
                total_distance += np.linalg.norm(self.component_positions[i] - self.component_positions[j]) # always pos.

        if total_distance == 0:
            reward = 1
        elif total_distance < self.previous_distance:
            reward = 0.5
        else:
            reward = 0

        self.previous_distance = total_distance
        return reward

    def check_overlap(self, pos1, pos2):
        x1, y1 = pos1
        x2, y2 = pos2

        return not (
                x1 + self.component_size[0] <= x2
                or x2 + self.component_size[0] <= x1
                or y1 + self.component_size[1] <= y2
                or y2 + self.component_size[1] <= y1
        )

def plot_placement(grid_size, component_size, component_positions, initial_component_positions):
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

    plt.savefig("shit_placement.png")


def lr_schedule(progress_remaining):
    initial_lr = 3e-3  # Start rate
    final_lr = 3e-4 # Minimum rate
    decay_rate = 2

    # Exponentially decayed learning rate
    return final_lr + (initial_lr - final_lr) * math.exp(-decay_rate * (1 - progress_remaining))

def object_placement():
    max_steps = 10000
    grid_size = 3000
    component_size = (576, 400)  # (576, 400)
    components_total = 4
    time_steps = 100000

    models_dir = f"ml_exploration/models/PPO-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    log_dir = f"ml_exploration/logs/PPO-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"


    env = make_vec_env(ComponentPlacementEnvironment, n_envs=24,
                               env_kwargs=dict(grid_size=grid_size, component_size=component_size,
                                               components_total=components_total, max_steps=max_steps))


    model = PPO("MlpPolicy", env, verbose=1, device="cpu", tensorboard_log=log_dir, learning_rate=0.03)

    # Folder structure
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    for i in range(1,6):
        model.learn(total_timesteps=time_steps, reset_num_timesteps=False, tb_log_name="PPO")
        model.save(f"{models_dir}/{time_steps*i}")

    trained_model = PPO.load(f"{models_dir}/200000", env=env)

    next_placements = env.reset()
    initial_placements = next_placements
    placements = []

    while True:
        action, _states = trained_model.predict(next_placements, deterministic=True)
        next_placements, reward, completed, truncated = env.step(action)

        if completed:
            break

        placements = next_placements # A hack to deal with SB3s auto reset when done = True

    env.close()

    print(f"Placement positions: {placements}")
    print(f"Initial Observation: {initial_placements}")
    plot_placement(grid_size=grid_size, component_size=component_size, component_positions=placements[0],
                   initial_component_positions=initial_placements[0])

    # tensorboard --logdir=ml_exploration/logs --bind_all
