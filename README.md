
# Analog-Automagic-Layout
___
### A Framework for Automatic Layout Generation of Analog Circuits Utilizing Open Source EDA Tools
___
### About
This repository is part of a master project in Electronic System Design at the Norwegian University of Science and Technology.

The source code provided here, which integrates with Carsten Wulff's Aicex repository 
(https://github.com/wulffern/aicex), attempts to automatically generate a Magic VLSI layout from a Xschem netlist.
This project is a proof-of-consept solution, and requires some understanding of the parameters provided in the TOML file
to create DRC/LVS clean layouts. The program has been tested for are some specific test circuits, achieving good results, 
but there are still likely many unhandled edge cases.  


### Setup
To build the Cython code go into the src/astar/ folder and run 'python3 setup.py build_ext --inplace'.


### Known limitations and bugs
- There is no support for the digital cells found within Carsten Wulff's Aicex 'TR' library of components.
- The 'united_res_cap' option in the TOML file is not working at the moment.









