from SPICE_parser import SPICEparser

PROJECT_DIR = "~/aicex/ip/jnw_bkle_sky130A/"
PROJECT_NAME = "JNW_BKLE"
PROJECT_NAME_LONG = "JNW_BKLE_SKY130A"

if __name__ == '__main__':
    print("[INFO]: Let's generate layout!")
    SPICEparser(project_name=PROJECT_NAME, project_dir=PROJECT_DIR)

