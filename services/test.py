arr = [1,2,4]
res = "".join('(' + str(i) + '), ' for i in arr)[:-2]
print(res)
