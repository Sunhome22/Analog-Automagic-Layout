import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split

# The following code is kinda like the "hello world" of Nerual Networks with pytorch.


class Model(nn.Module):
    # Input layer (4 features of the flower) -->
    # Hidden layer1 (number of neurons) -->
    # H2 (n) -->
    # output (3 classes of iris flowers)

    def __init__(self, input_features=4, h1=8, h2=9, output_features=3):
        super().__init__()  # instantiate our nn.Module
        self.fc1 = nn.Linear(input_features, h1)  # fully connected hidden layer 1
        self.fc2 = nn.Linear(h1, h2)  # fully connected hidden layer 2
        self.out = nn.Linear(h2, output_features)  # output layer

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.out(x)

        return x


def ml_flower_example():
    # print(torch.__version__)
    # print("CUDA available:", torch.cuda.is_available())

    torch.manual_seed(41)
    model = Model()

    # Load dataset
    my_df = pd.read_csv('ml_exploration/iris.csv')

    # Changed last colum from strings to floats
    my_df['variety'] = np.where(my_df['variety'] == 'Setosa', 0.0, my_df['variety'])
    my_df['variety'] = np.where(my_df['variety'] == 'Versicolor', 1.0, my_df['variety'])
    my_df['variety'] = np.where(my_df['variety'] == 'Virginica', 2.0, my_df['variety'])

    # Ensure numeric type by explicitly cast the column to a numeric type to ensure compatibility futher on
    my_df['variety'] = my_df['variety'].astype(float)

    # Train, test and split. We need to set and X and y
    X = my_df.drop('variety', axis=1)
    y = my_df['variety']

    # Converte these to numpy arrays
    X = X.values
    y = y.values

    # Train Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=41)

    # Convert X features to float tensors
    X_train = torch.FloatTensor(X_train)
    X_test = torch.FloatTensor(X_test)

    # Convert y features to float tensors
    y_train = torch.LongTensor(y_train)
    y_test = torch.LongTensor(y_test)

    # Set the cirterion of model to measure the error. How far off the predcions are we from the data
    criterion = nn.CrossEntropyLoss()

    # Choose an optimizer. The Adam optimizer is popular.
    # We also need to set our lr=learning rate.
    # If our error does not go down after a bunch of iterations (epochs), we want to lower our learning rate.

    # model.paramters() is our neural network, as specified in the __init__.
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # Train the model!
    # An epoch is one run thru all the training data in our network.
    # The data gets sendt thru layer 1 and layer 2 to the output within one epoch.
    epochs = 100
    losses = []  # keeping track for our losses

    for i in range(epochs):
        # Go forwards and get a prediction
        y_predicion = model.forward(X_train)  # Get predicted results

        # Measure the loss/error (this going to be high first)
        loss = criterion(y_predicion, y_train)

        # Keep track of our losses (helpfull for debugging)
        losses.append(loss.detach().numpy())

        # Print every 10 epochs
        if i % 10 == 0:
            print(f'Epoch: {i} and loss: {loss}')

        # Do some back propagation.
        # This involves taking the error rate of forward propagation and feed it back
        # thru the network to fine tune the weights.
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    # Graphing
    # We want to see that the loss/error drops (that means we have trained the model and it has learned)
    # If it isn't dropping we can tweak our learning rate or add more epochs.
    plt.plot(range(epochs), losses)
    plt.ylabel("loss/error")
    plt.xlabel("Epoch")
    plt.savefig("ml_exploration/ml_flower_example.png")

    # Evalute Model on Test data set (validate model on test set)
    with torch.no_grad():  # this basically turns off back propagation
        y_eval = model.forward(X_test)  # X_test are features from our test set, y_eval will be predictions
        loss = criterion(y_eval, y_test)  # Find the loss/error of y_eval vs. y_test

    correct = 0
    with torch.no_grad():
        for i, data in enumerate(X_test):
            y_val = model.forward(data)

            # This will tell us what type of flower class our network thinks it is
            print(f'{i+1}.) {str(y_val)} \t {y_test[i]} \t {y_val.argmax().item()}')

            # Correct or not
            if y_val.argmax().item() == y_test[i]:
                correct += 1

    print(f'We got {correct} correct!')



















