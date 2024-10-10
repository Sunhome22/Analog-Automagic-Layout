
# ================================================== Libraries =========================================================
from spice_parser import SPICEparser
from magic_layout_creator import MagicLayoutCreator
from utilities import Text, save_to_json, load_from_json
from dataclasses import dataclass, asdict
from magic_component_parser import MagicComponentsParser

# ========================================== Set-up classes and constants ==============================================


@dataclass
class ProjectProperties:
    directory: str
    name: str
    name_long: str
    standard_libraries: list


@dataclass
class StandardLibrary:
    name: str
    path: str


atr_lib = StandardLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_ATR_SKY130A")
tr_lib = StandardLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_TR_SKY130A")

project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       name="JNW_BKLE",
                                       name_long="JNW_BKLE_SKY130A",
                                       standard_libraries=[atr_lib, tr_lib])

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
    # found_stuff = load_from_json(file_name="components")
    # print(f"\n{Text.DEBUG} Components registered:")
    # for stuff in found_stuff:
    #     print(f"- {stuff}")

    # Create layout
    MagicLayoutCreator(project_properties=project_properties, components=components)

    # Temporary debugging
    print(f"\n{Text.DEBUG} Components registered:")
    for component in components:
        print(f"- {component}")


if __name__ == '__main__':
    main()



