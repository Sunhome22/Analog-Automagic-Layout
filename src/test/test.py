

seg_list={}
node = (2,1)

def main ():
    in_seg = False
    key = "placeholder"

    for k in seg_list:
        for i, seg in enumerate(seg_list[k]):
            if node in seg:
                in_seg = True
                index = i
                key = k
                break

    print(in_seg)
    print(type(index))
    print(key)
if __name__ == '__main__':
    main()