from curses.textpad import rectangle

import numpy as np
class Nets:
    applicable_nets:list
    pin_nets: list

    def __init__(self, applicable_nets: list, pin_nets:list):
        self.applicable_nets = applicable_nets
        self.pin_nets = pin_nets

def main():

    rectangles = [[6, 7, 4, 1]]
    start_real = (3,2)
    start_x, start_y = start_real if not rectangles else (rectangles[-1][2], rectangles[-1][3])

    print(start_x)
    print(start_y)




if __name__ == '__main__':
    main()



