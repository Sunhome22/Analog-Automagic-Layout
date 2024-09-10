import re
import os

class XSchem:

    def __init__(self):
        self.children = list()
        self.components = dict()
        self.name = ""
        self.path = ""

    def countPattern(self, pattern, line):
        count = len(re.findall("(" + pattern + ")", line))
        return count

    def parseBuffer(self,buff):

        d = buff[0]
        obj = None

        # Maps characters to their corresponding descriptors

        type_map = {
            "v": Version,
            "S": GlobalSpice,
            "V": GlobalVerilog,
            "G": GlobalVHDL,
            "E": GlobalTEDA,
            "K": GlobalProperties,
            "L": Line,
            "B": Rect,
            "P": Polygon,
            "A": Arc,
            "T": Text,
            "N": Wire,
            "C": Component,
            "[": EmbedSymbol
        }

        if d in type_map:
            obj = type_map[d]()
            # print(list(type_map.keys()).index(d) + 1)

        if obj is not None:
            obj.parse(buff)
            self.children.append(obj)

    def readFromFile(self, fname):

        self.name = os.path.basename(fname).replace(".sch", "")
        self.dirname = os.path.dirname(fname)

        with open(fname) as fi:
            buff = ""
            pcount = 0
            ind = 0
            for line in fi:
                ind += 1

                # - Check for symbol embedding
                if (re.search("^\[", line)):
                    raise Exception("Symbol Embedding on line %d not supported" % ind)

                # - Gobble up all {} with a stack
                start_p = self.countPattern("{", line)
                stop_p = self.countPattern("}", line)
                pcount += start_p - stop_p

                buff += line

                if (pcount == 0):
                    self.parseBuffer(buff)
                    buff = ""

        for c in self.children:
            if (c.isType("Component")):
                instanceName = c.name()
                if (instanceName):
                    self.components[instanceName] = c

    def toYaml(self):
        data = dict()

        for (key, o) in self.components.items():
            raise Exception("How should the yaml look???")


class Schematic(XSchem):

    def fromFile(self, fname):
        x = Schematic()
        x.readFromFile(fname)
        return x
    pass


class Object:
    def __init__(self, obj_type=None):
        self.properties = dict()
        self.obj_type = obj_type

    def parse(self,ss):
        self.ss = ss

    def property(self,key,val=None):
        if key in self.properties:
            if val:
                self.properties[key] = val
            return self.properties[key]
        else:
            return None

    def isType(self,typename):
        if self.__class__.__name__ == typename:
            return True
        elif super() and (super().__class__.__name__ == typename):
            return True
        return False

class Version(Object): pass
class GlobalSpice(Object): pass
class GlobalVerilog(Object): pass
class GlobalVHDL(Object): pass
class GlobalTEDA(Object): pass
class GlobalProperties(Object): pass
class Line(Object): pass
class Rect(Object): pass
class Polygon(Object): pass
class Arc(Object): pass
class Text(Object): pass
class Wire(Object): pass
class Component(Object): pass
class EmbedSymbol(Object): pass


class Component(Object):

    def __init__(self):
        super().__init__()
        self.symbol = None
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.flip = 0


    def parseProperties(self,ss):

        if re.search("^\s*$",ss):
            return

        ss = re.sub("\n"," ",ss).strip()

        key_value_pairs = re.findall(r'(?:[^\s"]|"(?:\\.|[^"])*")+',ss)
        for s in key_value_pairs:
            if re.search("^\s*$",s):
                continue
            ar = re.split("=",s)

            if len(ar) != 2:
                raise Exception("Don't know how to parse %s" %ar)


            (key,val) = ar
            self.properties[key] = val


    def name(self,val = None):
        return self.property("name",val)

    def parse(self,ss):
        super().parse(ss)
        m = re.search("C {([^}]+)} (\S+) (\S+) (\S+) (\S+) {([^}]*)}",ss,re.MULTILINE)

        if m:
            ar = m.groups()
            self.symbol = ar[0]
            self.x = ar[1]
            self.y = ar[2]
            self.rotation = ar[3]
            self.flip = ar[4]
            self.parseProperties(ar[5])
        else:
            raise Exception("Could not parse Component %s "%ss)