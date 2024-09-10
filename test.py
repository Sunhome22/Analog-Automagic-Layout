import os
from schematic_extractor.xschem import Schematic
from schematic_extractor.cell_builder import getLayoutCellFromXSch
from layout_creator.cell import Cell
from layout_creator.design import Design

def mag(ctx, lib, cell, libdir):
    """Translate a Xschem file to Magic"""

    xs = Schematic()

    xs.readFromFile(libdir + lib + os.path.sep + cell + ".sch")

    cell1 = getLayoutCellFromXSch(libdir, xs)

    # cell2 = cic.eda.cellfactory.getLayoutCellFromXSch(libdir,xs)
    Cell.moveTo(cell1.children[0], 10000, 20000)
    print(cell1.children[0])
    # cic.core.Cell.moveTo(cell2, 3, 4)

    # cic.core.Cell.moveTo(cell, 2, 3)
    # print(cic.core.Cell.moveTo(cell, 2, 3))

    design1 = Design()
    design1.add(cell1)

    # design1.add(cell2)
    print(f"Writing to {libdir + lib}")
    #obj = cic.MagicPrinter(libdir + lib, cell1)
    #obj.print(design1)


if __name__ == '__main__':
    mag(ctx=None, lib="JNW_BKLE_SKY130A", libdir="../aicex/ip/jnw_bkle_sky130A/design/", cell="JNW_BKLE")