# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import json
from circuit_components import Pin, Transistor, Capacitor, Resistor, LayoutPort, RectArea, TransformMatrix
from dataclasses import fields, is_dataclass
from typing import get_origin, get_args, List

# =============================================== Various utilities ====================================================

class Text:
    INFO = f"\033[38;2;{0};{255};{150}m{'[INFO]:'}\033[0m"
    ERROR = f"\033[38;2;{220};{0};{0}m{'[ERROR]:'}\033[0m"
    DEBUG = f"\033[38;2;{0};{100};{255}m{'[DEBUG]:'}\033[0m"


def save_to_json(objects: list, file_name: str):
    try:
        with open(f"{file_name}.json", 'w') as file:

            # Iterates over objects, serialize them and adds all class type attributes
            obj_dicts = [_serialize_dataclass(obj) for obj in objects]

            # Inserts JSON format from list of dicts into file
            json.dump(obj_dicts, file, indent=4)

        print(f"{Text.INFO} The file '{file_name}.json' was created")

    except Exception as e:
        print(f"{Text.ERROR} The file {file_name}.json could not be written due to: {e}")

def load_from_json(file_name: str):
        json_data = _open_json(file_name=file_name)
        components = []

        for obj in json_data:
            components.append(_deserialize_data(obj))

        print(components)


def _open_json(file_name: str):
    try:
        with open(f"{file_name}.json", 'r') as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"{Text.ERROR} The file {file_name}.json could not be found")

# Not working
def _deserialize_data(obj):
    class_table = {
        'Pin': Pin,
        'Transistor': Transistor,
        'Capacitor': Capacitor,
        'Resistor': Resistor,
        'LayoutPort': LayoutPort,
        'RectArea': RectArea,
        'TransformMatrix': TransformMatrix
    }

    # Get the dataclass type from the class table based on the class name from the JSON
    found_class = class_table[obj['__class__']]

    # Prepare the arguments for the constructor
    init_args = {}

    for field in fields(found_class):
        field_value = obj.get(field.name, None)  # Get the value or None if missing
        print(f"Handling field: {field.name} with value: {field_value}")  # Print each field being handled

        # Handle lists of dataclasses or other types
        if get_origin(field.type) == list:
            item_type = get_args(field.type)[0]  # Get the list's item type (can be LayoutPort in List[LayoutPort])
            if is_dataclass(item_type) and isinstance(field_value, list):
                # Recursively deserialize each item in the list
                field_value = [_deserialize_data(item) for item in field_value]

        # Handle nested dataclasses
        elif is_dataclass(field.type) and isinstance(field_value, dict):
            field_value = _deserialize_data(field_value)  # Recursively deserialize the nested dataclass

        # Set the field value, using defaults if applicable
        init_args[field.name] = field_value

    # Return the instantiated class with the deserialized arguments
    print(found_class(**init_args))
    return found_class(**init_args)


def _serialize_dataclass(obj):

    # Handle non-dataclasses
    if not is_dataclass(obj):
        return obj

    # Start building serialized output for the different dataclasses
    output = {'__class__': obj.__class__.__name__}

    for field in fields(obj):
        attribute = getattr(obj, field.name)

        # Check if the attribute is a dataclass
        if is_dataclass(attribute):

            # Recursively serialize nested dataclasses
            output[field.name] = _serialize_dataclass(attribute)

        # Check if the attribute is a list
        elif isinstance(attribute, list):

            # Serialize each item in the list
            output[field.name] = [_serialize_dataclass(item) for item in attribute]
        else:
            output[field.name] = attribute  # Just add the attribute

    return output