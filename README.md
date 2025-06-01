
# Analog-Automagic-Layout
___
### A Framework for Automated Layout Generation of Analog Circuits Utilizing Open Source EDA Tools
___
### About
This repository is part of a master thesis in Electronic System Design at the Norwegian University of Science and Technology (NTNU).

The source code provided here, which integrates with Carsten Wulff's Aicex repository, 
https://github.com/wulffern/aicex, is capable of taking in a hierarchy of schematics and generating an 
equivalent arrangement of layouts. The project as a whole is just a proof-of-consept solution, 
and requires some understanding of the parameters provided in the TOML file to create DRC/LVS clean layouts.

### Tests Performed

The implemented solution generated DRC clean and LVS compliant layout of a current mirror- and single stage OTA circuit 
in the SKY130 and SG13G2 technology nodes. These generations took approximately one minute.


### 3D View of Various Generated Layouts

SKY130:
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/current_mirror_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/single_stage_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/jnw_bkle_sky130a/refs/heads/main/design/JNW_BKLE_SKY130A/JNW_BKLE.gds.gltf

SG13G2:
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/lelo_bkle_ihp13g2/refs/heads/main/design/LELO_BKLE_IHP13G2/current_mirror_OTA.gds.gltf
- https://legacy-gltf.gds-viewer.tinytapeout.com/?model=https://raw.githubusercontent.com/analogicus/lelo_bkle_ihp13g2/refs/heads/main/design/LELO_BKLE_IHP13G2/single_stage_OTA.gds.gltf


### Known Limitations and Bugs
- Cell to cell routing is not implemented.
- There is no support for the digital cells found within Carsten Wulff's 'aicex' 'TR' library of components.
- The 'united_res_cap' option in the TOML file is not handled.
- Edge cases are present for the horizontal traces connecting to rails.









