
# ================================================== Libraries =========================================================
from spice_parser import SPICEparser
from magic_layout_creator import MagicLayoutCreator
from utilities import Text
from dataclasses import dataclass, asdict
from magic_component_parser import MagicComponentsParser
from json_converter import load_from_json, save_to_json

# ========================================== Set-up classes and constants ==============================================


@dataclass
class ComponentLibrary:
    name: str
    path: str


@dataclass
class ProjectProperties:
    directory: str
    name: str
    name_long: str
    component_libraries: list[ComponentLibrary]


# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_TR_SKY130A")
aal_lib = ComponentLibrary(name="AAL_LIB", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_AAL_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       name="JNW_BKLE",
                                       name_long="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib])

# ===================================================== Main ===========================================================


def main():

    print(f"{Text.INFO} Starting layout generation")

    # Extracts component information from SPICE file
    components = SPICEparser(project_properties=project_properties)

    # Update component attributes with information from it's associated Magic files
    components = MagicComponentsParser(project_properties=project_properties,
                                       components=components.get_info()).get_info()

    # Save found components to JSON file
    save_to_json(objects=components, file_name="components")

    # Read JSON file
    found_stuff = load_from_json(file_name="components")
    print(f"\n{Text.DEBUG} Components registered:")
    for stuff in found_stuff:
        print(f"- {stuff}")

    # Create layout
    MagicLayoutCreator(project_properties=project_properties, components=found_stuff)

    # Temporary debugging
    print(f"\n{Text.DEBUG} Components registered:")
    for component in components:
        print(id(component))
        print(f"- {component}")


if __name__ == '__main__':
    main()


