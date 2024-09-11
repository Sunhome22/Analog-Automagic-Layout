
from layout_creator.rect import Rect
from layout_creator.cell import Cell
from layout_creator.port import Port
from layout_creator.instance import Instance
from layout_creator.text import Text

class LayoutCell(Cell):

    def __init__(self):
        super().__init__()
        self.altenateGroup = False
        self.boundaryIgnoreRouting = False
        self.useHalfHeight = False
        self.meta = None
        self.graph = None


    def toJson(self):
        o = super().toJson()

        return o

    def fromJson(self,o):
        super().fromJson(o)

        if("alternateGroup" in o):
            self.alternateGroup = o["alternateGroup"]

        if("useHalfHeight" in o):
            self.useHalfHeight = o["useHalfHeight"]

        if("boundarIgnoreRouting" in o):
            self.boundaryIgnoreRouting = o["boundaryIgnoreRouting"]

        if("meta" in o):
            self.meta = o["meta"]

        if("graph" in o):
            self.graph = o["graph"]

        for child in o["children"]:

            c = None
            cl = child["class"]
            if(cl == "Rect"):
                c = Rect()
            elif(cl == "Port"):
                c  = Port()
            elif(cl == "Text"):
                c  = Text()
            elif(cl == "Instance"):
                c  = Instance()
            elif(cl == "Cell" or cl== "cIcCore::Route" or cl == "cIcCore::RouteRing" or cl == "cIcCore::Guard" or cl == "cIcCore::Cell" or cl == "cIcCore::LayoutCell"):
                c = LayoutCell()
            else:
                print(f"Unkown class {cl}")

            if(c is not None):
                c.design = self.design
                c.fromJson(child)
                self.add(c)
