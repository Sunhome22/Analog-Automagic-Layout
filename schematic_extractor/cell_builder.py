import os
import re

from layout_creator.instance import Instance
from schematic_extractor.magic import Layout
from schematic_extractor.magic import LayoutCell

cells = dict()
subcells = dict()

def getCellFromSymbol(libdir,symbol):
    path = libdir + symbol.replace(".sym",".mag")
    if(not os.path.exists(path)):
        raise Exception("Could not find %s" %(path))

    if("path" not in cells):
        lay = Layout()
        lay.readFromFile(path)
        cells[path] = lay
    return cells[path]

def getLayoutCellFromSchCell(libdir,schCell):
    names = schCell.name().split("_")

    layName = libdir + schCell.symbol.replace(".sym",".mag")

    lcell = Layout()
    lcell.readFromFile(layName)

    #print(names)
    #print(lcell)


    #raise Exception("Figure out to organize subcells")
    #- Should not return
    return lcell

def getInstanceFromComponent(layoutCell,component,x,y):
    i = Instance()
    i.instanceName = component.name()
    i.name = component.name()
    i.cell = layoutCell.name
    i.libpath = layoutCell.libpath
    i.xcell = x
    i.ycell = y
    return i

def getLayoutCellFromXSch(libdir,xs):

    root = Layout()
    root.name = xs.name
    root.dirname = xs.dirname

    y = 0
    x = 0

    for instanceName in xs.components:

        scell = xs.components[instanceName]
        #- TODO: Figure out how to handle ports
        if("devices/" in scell.symbol):
            continue

        #- Categorise based on name <ident>_<ident>_<nr>

        #raise Exception("Figure out how to organize subcells")

        lcell = getLayoutCellFromSchCell(libdir,scell)

        name = scell.name()

        match = re.findall(r"\[(\d+:\d+)\]",name)
        if(match): #- Multiple instances
            ly = y
            lx = 0
            local_cell = LayoutCell()

            if(len(match) > 1):
                raise Exception("Name contains duplicate [d:d] %s"%str(match))
            #- Assume 1 match, anything else is an error
            (end,start) = re.split(":",match[0])
            for i in range(int(start),int(end)):
                i = getInstanceFromComponent(lcell,scell,x,ly)
                local_cell.add(i)
                ly += lcell.height()

            root.add(local_cell)

        else: #- Single instance
            i = getInstanceFromComponent(lcell,scell,x,y)
            root.add(i)
        x += lcell.width()


    root.updateBoundingRect()

    return root