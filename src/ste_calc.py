import math

def calculate_mean(data):
    return sum(data) / len(data)

def calculate_standard_deviation(data):
    mean = calculate_mean(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    return (mean, math.sqrt(variance))

# Example list of 20 timing values in milliseconds
timings = [1868.328314238228, 1834.4244121620432, 1785.6237639812753, 1788.0332858292386, 1990.4191254256293, 2189.5326294722036, 2060.141115714796, 2041.3662911234424, 1902.1044388515875, 1860.3347677979618, 1858.5348977362737, 1847.2858816348016, 1858.7114340336993, 1848.7740684524179, 1843.105880284682, 1822.850193365477, 1804.1171388970688, 1818.7719652587548, 1809.394137837924, 1814.3702529054135]
time_result = calculate_standard_deviation(timings)

print("Time:"+str(time_result[0])+"(+-)"+str(time_result[1]))