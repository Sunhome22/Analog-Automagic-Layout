from SPICE_parser import SPICEparser
from Magic_layout_creator import MagicLayoutCreator
from utilities import TextColor

PROJECT_DIR = "~/aicex/ip/jnw_bkle_sky130A/"
PROJECT_NAME = "JNW_BKLE"
PROJECT_NAME_LONG = "JNW_BKLE_SKY130A"
STANDARD_LIBS = ["JNWTR", "JNWATR"]


if __name__ == '__main__':
    print(f"{TextColor.INFO} Starting layout generation")
    components = SPICEparser(project_name=PROJECT_NAME, project_directory=PROJECT_DIR, standard_libraries=STANDARD_LIBS)
    MagicLayoutCreator(project_name=PROJECT_NAME, project_name_long=PROJECT_NAME_LONG,
                       project_dir=PROJECT_DIR, components=components.get())


