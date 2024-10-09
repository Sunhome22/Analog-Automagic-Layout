# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import json
import sys
from circuit_components import *
from dataclasses import fields, is_dataclass, asdict
from typing import get_origin, get_args, List

# =============================================== Various utilities ====================================================

class Text:
    INFO = f"\033[38;2;{0};{255};{150}m{'[INFO]:'}\033[0m"
    ERROR = f"\033[38;2;{220};{0};{0}m{'[ERROR]:'}\033[0m"
    DEBUG = f"\033[38;2;{0};{100};{255}m{'[DEBUG]:'}\033[0m"


# Dictionary to map class names to their corresponding classes
classes_map = {
    "Pin": Pin,
    "Transistor": Transistor,
}


def save_to_json(objects: list, file_name: str):
    try:
        with open(f"{file_name}.json", 'w') as file:

            # Iterates over objects, serialize them and adds all class type attributes
            obj_dicts = [_serialize_dataclass(obj) for obj in objects]
            #obj_dicts = [asdict(component) for component in objects]

            # Inserts JSON format from list of dicts into file
            json.dump(obj_dicts, file, indent=4)

        print(f"{Text.INFO} The file '{file_name}.json' was created")

    except Exception as e:
        print(f"{Text.ERROR} The file {file_name}.json could not be written due to: {e}")


def load_from_json(file_name: str):
    json_data = _open_json(file_name=file_name)

    load_shit(json_data)
    components = []


def load_shit(json_data):
    loaded_components = []
    #for obj in json_data:
    #    component.append(deserialize_dataclass(obj))
    component_map = {"Transistor": Transistor,
                     "Resistor": Resistor,
                     "LayoutPort": LayoutPort,
                     "RectArea": RectArea}

    # Not working still, but closer
    for obj in json_data:
        print("NEW OBJECT")
        if '__class__' in obj and obj['__class__'] in component_map:
            component_class = component_map[obj['__class__']]

            # First load
            loaded_component = component_class(**{key: value for key, value in obj.items() if key != '__class__'})
            print(loaded_component)
            for i in obj.values():
                if isinstance(i, list):
                    for j in i:
                        if '__class__' in j and j['__class__'] in component_map:
                            nested_class = component_map[j['__class__']]
                            nested_component = nested_class(**{key: value for key, value in j.items() if key != '__class__'})
                            print(nested_component)

                            for k in j.values():
                                if '__class__' in k and k['__class__'] in component_map:
                                    lvl2_nested_class = component_map[k['__class__']]
                                    lvl2_component = lvl2_nested_class(**{key: value for key, value in k.items() if key != '__class__'})


def _open_json(file_name: str):
    try:
        with open(f"{file_name}.json", 'r') as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"{Text.ERROR} The file {file_name}.json could not be found")


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