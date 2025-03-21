


def my_case(index, length, switch_bool):

    conditions = {
        "case1" : [index == 0, length ==1],
        "case2" : [index == 0, length>1, switch_bool],
        "case3": [index == 0, length > 1, not switch_bool],
        "case4": [index == length-1, switch_bool],
        "case5": [index == length-1, not switch_bool],
    }



    match (index, length, switch_bool):

        case (index, length, switch_bool)if all(conditions["case1"]) :
            return 0,0
        case (index, length, switch_bool) if all(conditions["case2"]):
            return -trace_width//2, 0
        case (index, length, switch_bool) if all(conditions["case3"]):
            return 0, trace_width//2
        case (index, length, switch_bool) if all(conditions["case4"]):
            return 0, trace_width//2
        case (index, length, switch_bool) if all(conditions["case5"]):
            return -trace_width//2
        case (index, length, switch_bool):
            return -trace_width//2, trace_width//2



def main():
#index
#length
#switch bool
    var = [1,2,0]
    my_case(var[0], var[1], var[2])
if __name__ == '__main__':
    main()


    if index == 0 and length == 1:
        return 0, 0
    elif index == 0 and length > 1:

        if switch_bool:
            return -x // 2, 0
        else:
            return 0, x // 2

    elif index == length - 1:
        if switch_bool:
            return 0, x // 2
        else:
            return -x// 2, 0
    else:
        return -x // 2, x // 2