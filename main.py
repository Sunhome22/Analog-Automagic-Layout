#!/home/bjorn/Analog-Automagic-Layout/venv/bin/python
# ==================================================================================================================== #
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #


# ================================================== Libraries =========================================================

from ml_exploration.ml_flower_example import ml_flower_example
from ml_exploration.dqn_learning_example import ml_dqn_example

# ========================================== Set-up classes and constants ==============================================

# ===================================================== Main ===========================================================


def main():
    ml_flower_example()
    # ml_dqn_example()

if __name__ == '__main__':
    main()
