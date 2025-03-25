





def main():
    grid = [[0 for _ in range(20)] for _ in range(20)]
    segment = [(10,10), (10,11), (10,12), (10,13),(10,14)]
    p =  0
    for x, y in segment:
        for i in range(-2,3):
            for p in range(-4, 5):
                grid[y + p][x + i] = 1

    for row in grid:
        print(row)



if __name__ == '__main__':
    main()
