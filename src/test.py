def main():

    test_dict = {
        "t1":{ "t2": [1, 2 , 3],
                "t3": [4, 5 , 6]},


        "s2":{ "t2": [1, 2 , 3],
                "t3": [4, 5 , 6]},
        "s3": {"t2": [1, 2, 3],
               "t3": [4, 5, 6]}


        }

    merged = {"t2": [], "t3": []}

    for subdict in test_dict.values():
        merged["t2"].extend(subdict.get("t2", []))
        merged["t3"].extend(subdict.get("t3", []))

    print(merged)



if __name__ == '__main__':
    main()
