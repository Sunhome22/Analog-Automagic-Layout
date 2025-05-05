### Things to implement/fix
- [ ] Start creating basic test to circuit_spice_parser. Pytest will be used
- [ ] Mabye update found vias and inbetween placed metal layers to JSON file after layout creation has completed.
  (Don't think this really makes sense to do)
- [x] Handle bulks accidently overlapping for the diffpair of the original comparator circuit 
- [x] Implement structural component creator and deal with pins
- [x] Make config file for user input variables for linear optimization
- [ ] Number ID begins at zero again when dealing with trace nets. Maybe fix?
- [ ] There is likely some bug with connection points still, resulting in to many being created on top of each other.
- [ ] Fix <<>> and rect in .mag file. Reduce <<>> count
- [x] Fix x,y offset of rail rings
- [x] Fix number of traces and vias added, since its double, due to the implementation of local_bulk_to_rail_connection
- [x] Add vias to TraceNet and update .json file
- [x] Having to write MN1 or MP1 is a fair solution according to Carsten. 
- [x] Remove layer name dependency of technology from magic layout creator. 
- [ ] When adding multiple circuit cells the set of components only getting added once. 
- [ ] Fix gathering of deeper information when cells inherit other cells. Overlap distance is for example not handled
- [x] Fix missing rail and tap in a specific layout edge case (see .json file)
- [x] Deal with 15 vs 16 net missmatch when placing multiple cell within each other but not connected.
- [x] How many VDD nets is common to have. Is it ok to assume all cells have the same number of VDD nets?

## Notes
- Vias get turned into multiple smaller ones when converting to GDSII. Always want atleast two, however
  Carsten is not allways following this rule.

- Designers can make ther on transistors as they which. After that he need to create labels to define what is G,S,D,B
- Everything that is white in Magic is connected together if its transistors of the same type. You need a deep nwell 
  for example if want to differentiate two sets of NMOSes. 

- Would be nice if A* logged out what trace it is currently solving
- Alf has been told by Carsten to always connect bulk to VSS/VDD
- Carsten is going to add nsubstratendiff and pstubstreatepdiff layers to cic that I can use
- Place nsubstratendiff and pstubstreatepdiff around a group of transistors and place locali metal on top and bottom. 
  Afterwards connet it to VSS or VDD.
- It is very possible to have multiple VDDs. That should just be added to the ring outside. 
- All rails should be in m1 so you can connect from either below or above
- You need to write an "x" (instance name) at the front of names in the schematic. 
- Our system does not use instance names defined by xschem, we roll our one.
- Were the ports should be, could be a specification like top, bottom, left, right of cell.
- Is it safe to say that all components always will have a FIXED_BBOX parameter? No
- Do routing in m3 and m4


- Running unit_res_cap is not working.
- Area allowed to route in needs to be fixed for the 50f cap
- Sub cell distance should have a value between each sub cell and not one for all!

## Notes on running multiple cells
- Spice parsing and magic layout parsing will happen once also. 
- MagicLayoutCreator is going to be ran once on all components.
- Trace generator will run multiple times for each cell. There shall only be one CircuitCell in it every time.
- A lot of filtering is going be happening here. 
- 
- Spice parser first just looks at every cell defined and appends that to circuit_cells. Then within 
- "__add_components_for_each_circuit_cell" a circuit cell get properly added for every unique cell (deals with
- nested cells). In cell creator for each iteration we deal with components with the same cell chain. 
- In Magic layout creator's "_generate_magic_files" magic files get created 

