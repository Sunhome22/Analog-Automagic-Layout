import os
import schematic_extractor.xschem
import schematic_extractor.cell_builder
import layout_creator.cell
import layout_creator.design
import layout_creator.rect
import layout_creator.printer.magicprinter

def sch_to_mag(lib, lib_dir, cell):

    # Create schematic object and read schematic file
    sch = schematic_extractor.xschem.Schematic()
    sch.readFromFile(lib_dir + lib + os.path.sep + cell + ".sch")

    # Build cell
    cell = schematic_extractor.cell_builder.getLayoutCellFromXSch(lib_dir, sch)

    # Try som moving of child in the cell
    layout_creator.cell.Cell.moveTo(cell.children[0], 20000, 20000)

    # Add cell to Magic design
    design = layout_creator.design.Design()
    design.add(cell)

    # Print design to Magic
    obj = layout_creator.printer.magicprinter.MagicPrinter(lib_dir + lib, cell)
    obj.print(design)


if __name__ == '__main__':
    sch_to_mag(lib="JNW_BKLE_SKY130A", lib_dir="../aicex/ip/jnw_bkle_sky130A/design/", cell="JNW_BKLE")