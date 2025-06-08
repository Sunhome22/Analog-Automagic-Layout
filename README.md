
# Analog-Automagic-Layout
___
### A Framework for Automated Layout Generation of Analog Circuits Utilizing Open Source EDA Tools
___
### About
This repository is part of a Master's Thesis in Electronic Systems Design at the Norwegian University of Science and Technology (NTNU).

The source code provided here, which integrates with Carsten Wulff's Aicex repository, 
https://github.com/wulffern/aicex, is capable of taking in a hierarchy of schematics and generating an 
equivalent arrangement of layouts. The project as a whole is just a proof-of-consept solution, 
and requires some understanding of the parameters provided in the TOML file to create DRC/LVS clean layouts. 
The program is designed to work with Xschem and Magic VLSI.

### Tests Performed

The implemented solution generated DRC clean and LVS compliant layout of a current mirror- and single stage OTA circuit 
in the SKY130 and SG13G2 technology nodes. These generations took approximately one minute. 

A larger bandgap temperature sensor has also been tested, but cell to cell routing is not implmented. 
This resulted in a DRC clean layout, but not completely LVS correct. The generation time for this circuits 74 components was approximatly 30 minutes, however almost all of that 
time was spent on placement for one cell with a larger number of components. The number of placement constraints scales exponentially with the number of components. 


### 3D View of Various Generated Layouts

SKY130:
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/current_mirror_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/single_stage_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/JNW_BKLE.gds.gltf

SG13G2:
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/lelo_bkle_ihp13g2/refs/heads/main/design/LELO_BKLE_IHP13G2/current_mirror_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/lelo_bkle_ihp13g2/refs/heads/main/design/LELO_BKLE_IHP13G2/single_stage_OTA.gds.gltf


### Setup
The provided `src/main.py` shows what a typical setup looks like.

### Known Limitations and Bugs
- Cell to cell routing is not implemented.
- There is no support for the digital cells found within Carsten Wulff's 'aicex' 'TR' library of components.
- Edge cases are present for the horizontal traces connecting to rails.
- The 'united_res_cap' option in the TOML file is not handled.










