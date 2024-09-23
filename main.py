from SPICE_parser import SPICEparser
from Magic_layout_creator import MagicLayoutCreator
from utilities import TextColor
from dataclasses import dataclass

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

if __name__ == '__main__':
    print(f"{TextColor.INFO} Starting layout generation")
    components = SPICEparser(project_properties=project_properties)
    MagicLayoutCreator(project_properties=project_properties, components=components.get())


