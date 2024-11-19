# ================================================== Libraries =========================================================
from circuit.circuit_spice_parser import SPICEparser
from magic.magic_layout_creator import MagicLayoutCreator
from dataclasses import dataclass, asdict
from magic.magic_component_parser import MagicComponentsParser
from json_tool.json_converter import save_to_json, load_from_json
from logger.logger import get_a_logger
from circuit.circuit_components import Trace, RectAreaLayer, RectArea
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
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       name="JNW_BKLE",
                                       name_long="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib, misc_lib])

# ===================================================== Main ===========================================================


def main():

    # Create a logger
    logger = get_a_logger(__name__)

    # Extracts component information from SPICE file
    components = SPICEparser(project_properties=project_properties)

    # Update component attributes with information from it's associated Magic files
    components = MagicComponentsParser(project_properties=project_properties,
                                       components=components.get_info()).get_info()

    # Save found components to JSON file
    save_to_json(objects=components, file_name="json_tool/components.json")

    # Read JSON file
    found_stuff = load_from_json(file_name="json_tool/ResultV21.json")

    # An example trace
    a_trace = Trace()
    a_trace.instance = a_trace.__class__.__name__  # add instance type
    a_trace.number_id = 0
    a_trace.name = "16G-17G"
    a_trace.segments.append(RectAreaLayer(layer="locali", area=RectArea(x1=300, y1=0, x2=450, y2=50)))
    a_trace.vias.append(RectAreaLayer(layer="viali", area=RectArea(x1=300, y1=0, x2=350, y2=50)))
    a_trace.segments.append(RectAreaLayer(layer="m1", area=RectArea(x1=300, y1=0, x2=350, y2=300)))
    found_stuff.append(a_trace)

    save_to_json(objects=found_stuff, file_name="json_tool/test.json")

    # Create layout
    MagicLayoutCreator(project_properties=project_properties, components=found_stuff)

    # Debug log of all components
    logger.debug(f"Components registered: ")
    for component in components:
        logger.debug(f"- {component}")


if __name__ == '__main__':
    main()



