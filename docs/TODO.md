### Things to implement/fix
- Start creating basic test to circuit_spice_parser. Pytest will be used
- Mabye update found vias and inbetween placed metal layers to JSON file after layout creation has completed.
  (Don't think this really makes sense to do)
- Handle bulks accidently overlapping for the diffpair of the original comparator circuit [V]
- Implement structural component creator and deal with pins [V]
- Create separate object for functional and structural components 
- Make config file for user input variables for linear optimization [V]
- Number ID begins at zero again when dealing with trace nets. Maybe fix?