import numpy as np

seg_list={}
node = (2,1)

def main1 ():
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



def _eliminate_segments1(seg_list, scale_factor):
    spacing_m2 = 14 #vertical
    spacing_m3 = 30 #horizontal

    for key in seg_list:
        duplicate_list = seg_list[key][:]
        removal_list_indexes = []
        for index_1, path_segment_1 in enumerate(seg_list[key]):
            for index_2, path_segment_2 in enumerate(duplicate_list):
                if path_segment_1[0][0] - path_segment_1[1][0] == path_segment_2[0][0] - path_segment_2[1][0] == 0 and path_segment_1 != path_segment_2: #horizontal, m3
                    if path_segment_1[0][1]-path_segment_2[0][1] <=30+30/scale_factor:
                        removal_list_indexes.append((index_1,index_2))


                elif path_segment_1[0][1] - path_segment_1[1][1] == path_segment_2[0][1] - path_segment_2[1][1] == 0 and path_segment_1 != path_segment_2: #vertical, m2
                    if path_segment_1[0][0]-path_segment_2[0][0] <=30+14/scale_factor:
                        removal_list_indexes.append((index_1, index_2))


        removal_list_indexes = _remove_duplicates(removal_list_indexes)
        temp_removal_list = [removal_list_indexes[0][0]]
        for element in removal_list_indexes:
            if element[0][0] == temp_removal_list[0]:
                temp_removal_list.append(element[0][1])

        removal_list_indexes = removal_list_indexes[len(temp_removal_list):]

        longest = None
        for element in temp_removal_list:
            if longest == None:
                longest = element
            elif len(seg_list[key][element]) > len(seg_list[key][longest]):
                longest = element

        for element in temp_removal_list:
            if element != longest:
                remove = seg_list[key][element]
                seg_list[key].remove(remove)

    return

def main():
    dist = np.linalg.norm([2 ,2] - [5, 0])

    print(dist)

if __name__ == '__main__':
    main()


