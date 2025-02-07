import numpy as np
class Nets:
    applicable_nets:list
    pin_nets: list

    def __init__(self, applicable_nets: list, pin_nets:list):
        self.applicable_nets = applicable_nets
        self.pin_nets = pin_nets

def main():
    net_list = Nets(applicable_nets=[], pin_nets=[])

    net_list.applicable_nets = ["net1", "net2", "net3"]
    net_list.pin_nets = ["VDD", "VSS", "Pin1", "Pin2"]



    net_example = ["net1", "net2", "local:net1", "local:net2", "local:VDD", "Local:VSS"]






if __name__ == '__main__':
    main()


