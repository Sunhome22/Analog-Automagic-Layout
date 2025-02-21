### Things to implement/fix
- [ ] Start creating basic test to circuit_spice_parser. Pytest will be used
- [ ] Mabye update found vias and inbetween placed metal layers to JSON file after layout creation has completed.
  (Don't think this really makes sense to do)
- [x] Handle bulks accidently overlapping for the diffpair of the original comparator circuit 
- [x] Implement structural component creator and deal with pins
- [ ] Create separate object for functional and structural components 
- [x] Make config file for user input variables for linear optimization
- [ ] Number ID begins at zero again when dealing with trace nets. Maybe fix?
- [ ] There is likely some bug with connection points still, resulting in to many being created on top of each other.


## Notes
- Vias get turned into multiple smaller ones when converting to GDSII. Always want atleast two, however
  Carsten is not allways following this rule.

- Designers can make ther on transistors as they which. After that he need to create labels to define what is G,S,D,B

- Why are we using the transistor we are?

- Would be nice if A* logged out what trace it is currently solving

- Alf has been told by Carsten to always connect bulk to VSS/VDD
- Carsten is going to add nsubstratendiff and pstubstreatepdiff layers to cic that I can use
- Place nsubstratendiff and pstubstreatepdiff around a group of transistors and place locali metal on top and bottom. 
  Afterwards connet it to VSS or VDD.
- It is very possible to have multiple VDDs. That should just be added to the ring outside. 
- All rails should be in m1 so you can connect from either below or above
- You need to write an "x" at the front of names in the schematic
- Were the ports should be, could be a specification like top, bottom, left, right of cell.

## Notes on running multiple cells
- Spice parsing and magic layout parsing will happen once also. 
- MagicLayoutCreator is going to be ran once on all components.
- Trace generator will run multiple times for each cell. There shall only be one CircuitCell in it every time.
- A lot of filtering is gonna be happening here. 
