#======================================================================================================================#
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
#======================================================================================================================#
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
#======================================================================================================================#


# ================================================== Libraries =========================================================
import json
from circuit.circuit_components import *
from dataclasses import asdict
from typing import List
from logger.logger import get_a_logger
# =============================================== JSON converter =======================================================

logger = get_a_logger(__name__)


def save_to_json(objects: list, file_name: str):
    try:
        with open(file_name, 'w') as file:

            # Iterates over objects, serialize them and adds all class type attributes
            obj_dicts = [asdict(component) for component in objects]  # new method

            # Inserts JSON format from list of dicts into file
            json.dump(obj_dicts, file, indent=4)

        logger.info(f"The file '{file_name}' was created")

    except Exception as e:
        logger.error(f"The file {file_name} could not be written due to: {e}")


def load_from_json(file_name: str):
    components = []

    # This needs to be manually update if new components are added!
    component_instances = {"Transistor": Transistor,
                           "Resistor": Resistor,
                           "Capacitor": Capacitor,
                           "Pin": Pin,
                           "Cell": CircuitCell,
                           "Trace": Trace}
    # Read JSON file
    try:
        with open(file_name, 'r') as file:
            json_data = json.load(file)

    except FileNotFoundError:
        logger.error(f"'{file_name}' could not be found")

    # Loop over JSON data
    for component in json_data:

        # Match instance with class type, add all dict attributes with '__post_init__' methods in the dataclasses,
        # and append each found component to a list

        if 'instance' in component and component['instance'] in component_instances:
            component_class = component_instances[component['instance']]
            loaded_component = component_class(**component)
            components.append(loaded_component)

    logger.info(f"The file '{file_name}' was loaded")

    return components
