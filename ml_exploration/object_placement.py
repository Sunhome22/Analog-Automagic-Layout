from curses.textpad import rectangle

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches
import pandas as pd
from sklearn.model_selection import train_test_split

# one object with one connection

WIDTH = 100
HEIGHT = 100


class Model(nn.Module):
    # Input layer (4 features of the flower) -->
    # Hidden layer1 (number of neurons) -->
    # H2 (n) -->
    # output (3 classes of iris flowers)

    def __init__(self, input_features=11, h1=8, h2=9, output_features=11):
        super().__init__()  # instantiate our nn.Module
        self.fc1 = nn.Linear(input_features, h1)  # fully connected hidden layer 1
        self.fc2 = nn.Linear(h1, h2)  # fully connected hidden layer 2
        self.out = nn.Linear(h2, output_features)  # output layer

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.out(x)

        return x


def object_placement():
    torch.manual_seed(1)
    model = Model()
    

    # model.paramters() is our neural network, as specified in the __init__.
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)




def show_results():
    print("Stuff got placed")
    fig, ax = plt.subplots()

    rect = patches.Rectangle((100, 100), WIDTH, HEIGHT, facecolor='r')
    ax.add_patch(rect)
    plt.xlim(0, 1000)
    plt.ylim(0, 1000)
    plt.savefig("shit_placement.png")