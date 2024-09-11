import sys

from layout_creator.rect import Rect
from layout_creator.subckt import Subckt

class Cell(Rect):

    def toMicron(self, angstrom):
        return (angstrom / 10) / 1000.0

    def __init__(self, name=""):
        super().__init__()
        self.subckt = None
        self.name = name
        self.ignoreBoundaryRouting = False
        self.physicalOnly = False
        self.abstract = False
        self.children = list()
        self.ports = dict()
        self.routes = list()
        self.ckt = None
        self.design = None
        self.symbol = ""
        self.prefix = ""
        self.physicalOnly = False
        self.libCell = False
        self.isUsed = False
        self.libpath = ""
        self.has_pr = False
        self.obj = False  # - Original JSON obj

    # Find the first rectangle in this cell that uses layer
    def getRect(self, layer):
        raise Exception("Not implemented")
        pass

    # Add a rectangle to the cell, hooks updated() of the child to updateBoundingRect
    def add(self, child):
        if (child == None):
            raise Exception("Null rectangle added")

        if (child.isPort()):
            self.ports[child.name] = child

        if (not child in self.children):
            if (child.isRoute()):
                self.routes.append(child)
            child.parent = self
            self.children.append(child)
            child.connect(self.updateBoundingRect)

    # Move this cell, and all children by dx and dy
    def translate(self, dx, dy):
        super().translate(dx, dy)
        for child in self.children:
            child.translate(dx, dy)
        self.updateBoundingRect()
        self.emit_updated()

    # Mirror this cell, and all children around ax
    def mirrorX(self, ax):
        super().mirrorX(ax)
        for child in self.children:
            child.mirrorX(ax)
        for port in self.ports:
            port.mirrorX(ax)
        self.updateBoundingRect()
        self.emit_updated()

    # Mirror this cell, and all children around ay
    def mirrorY(self, ay):
        super().mirrorY(ay)
        for child in self.children:
            child.mirrorY(ay)
        for port in self.ports:
            port.mirrorY()
        self.updateBoundingRect()
        self.emit_updated

    # Move this cell, and all children to ax and ay
    def moveTo(self, ax, ay):
        x1 = self.x1
        y1 = self.y1
        super().moveTo(ax, ay)
        for child in self.children:
            child.translate(ax - x1, ay - y1)
        self.updateBoundingRect
        self.emit_updated()

    # Center this cell, and all children on ax and ay
    def moveCenter(self, ax, ay):
        self.updateBoundingRect()

        xc1 = self.centerX
        yc1 = self.centerY

        xpos = self.left - (xc1 - ax)
        ypos = self.bottom - (yc1 - ay)

        self.moveTo(xpos, ypos)

    # Shortcut for adding ports
    def addPort(name, rect):
        raise Exception("Not implemented")
        pass

    # Mirror this cell, and all children around horizontal center point (basically flip horizontal)
    def mirrorCenterX(self):
        self.mirrorX(self.centerY)
        pass

    def mirrorCenterY(self):
        self.mirrorY(self.centerX)
        pass

    def updateBoundingRect(self):
        r = self.calcBoundingRect()
        self.setRect(r)
        pass

    # Calculate the extent of this cell. Should be overriden by children
    def calcBoundingRect(self):
        x1 = sys.maxsize
        y1 = sys.maxsize
        x2 = - sys.maxsize - 1
        y2 = - sys.maxsize - 1

        if (len(self.children) == 0):
            x1 = y1 = x2 = y2 = 0

        for child in self.children:
            if (self.ignoreBoundaryRouting and
                    (not (child.isInstance()) or not (child.isCut()))):
                continue
            cx1 = child.x1
            cx2 = child.x2
            cy1 = child.y1
            cy2 = child.y2

            if (cx1 < x1):
                x1 = cx1
            if (cy1 < y1):
                y1 = cy1
            if (cx2 > x2):
                x2 = cx2
            if (cy2 > y2):
                y2 = cy2

        r = Rect()

        r.setPoint1(x1, y1)
        r.setPoint2(x2, y2)

        return r

    def isEmpty(self):
        if (self.name == ""):
            return True
        return False

    def fromJson(self, o):
        super().fromJson(o)
        self.prefix = self.design.prefix
        self.name = self.design.prefix + o["name"]

        if ("meta" in o and "symbol" in o["meta"]):
            self.symbol = o["meta"]["symbol"]
        else:
            self.symbol = self.name

        if ("has_or" in o):
            self.has_pr = o["has_pr"]

        if ("libpath" in o):
            self.libpath = o["libpath"]

        if ("abstract" in o):
            self.abstract = o["abstract"]

        if ("physicalOnly" in o):
            self.physicalOnly = o["physicalOnly"]

        if ("libcell" in o):
            self.libcell = o["libcell"]

        if ("cellused" in o):
            self.isUsed = o["cellused"]

        # - Handle subckt
        if ("ckt" in o):
            self.ckt = Subckt()
            self.ckt.prefix = self.design.prefix
            self.ckt.fromJson(o["ckt"])

    def toJson(self):
        o = super().toJson()
        o["class"] = self.__class__.__name__
        o["name"] = self.name
        o["has_pr"] = self.has_pr

        ckt = self.ckt
        o["ckt"] = dict()
        if (ckt is not None):
            ockt = ckt.toJson()
            o["ckt"] = ockt

        oc = list()
        for child in self.children:
            oc.append(child.toJson())
        o["children"] = oc
        return o

    def __str__(self):
        return super().__str__() + " name=%s " % (self.name)

    def toSkill(self):
        name = "cw" + self.name
        ss = f"""
        {name} = makeTable("{name}" "")
        {name}["x"] = {self.toMicron(self.x1)}
        {name}["y"] = {self.toMicron(self.y1)}
        {name}["width"] = {self.toMicron(self.width())}
        {name}["height"] = {self.toMicron(self.height())}
        """
        return ss

    def getCell(self, cellname):
        if (cellname in self.design.cells):
            return self.design.cells[cellname]
        return None

    def startswith(self, ss):
        if (self.name.startswith(self.prefix + ss)):
            return True
        return False