class Node:
    def __init__(self, value):
        self.value = value
        self.parents = []
        self.children = []
        
    def add_relation(self, parent = None, child = None):
        if parent is not None:
            self.parents.append(parent)
            parent.children.append(self)
        if child is not None:
            self.children.append(child)
            child.parents.append(self)

    def assign_relation(self, parent = None, child = None):
        if parent is not None:
            self.parents = parent
        if child is not None:
            self.children = child

    def get_par(self):
        parents = [parent.value for parent in self.parents]  # Извлекаем значения родителей
        children = [child.value for child in self.children]  # Извлекаем значения детей
        return self.value, parents, children



# Функция для обхода дерева по ширине
def breadth_first_traversal_with_levels(root):
    # print('+++++++++++++++++++++')
    if not root:
        return []

    queue = [(root, 0)]  # Очередь: (узел, уровень)
    result = []  # Список для хранения результата
    res = {}  # Список для хранения результата

    visited = set()  # Для отслеживания посещенных узлов (чтобы избежать бесконечных циклов)

    while queue:
        node, level = queue.pop(0)
        # print("1. {} {} {}".format(node.value, level, visited))

        # Если узел уже обработан, пропускаем его
        if node.value in visited:
            continue
            
        # Добавляем узел в результат
        if level not in res:
            res[level] = []
        res[level].append(node.value)

        result.append((node.value, level))
        visited.add(node.value)
        # print("2. {} {} {}".format(node.value, level, visited))

        # Добавляем родителей узла в очередь с уровнем +1
        for parent in node.parents:
            queue.append((parent, level + 1))
            # print("3. {} {}".format(parent.value,level + 1))

        # Добавляем детей узла в очередь с уровнем -1
        for child in node.children:
            queue.append((child, level - 1))
            # print("3. {} {}".format(child.value,level - 1))
    # print('+++++++++++++++++++++')
    return result,res


# Создание дерева с добавлением узла "H" как ребенка B и C assign_relation
root = Node("Я")

h = Node("Брат")

i = Node("Сын")

b = Node("Мама")
c = Node("Папа")

d = Node("Бабушка1")
e = Node("Дедушка1")

j = Node("Тетя")
k = Node("Дядя")
l = Node("Двоюродный брат")

f = Node("Бабушка2")
g = Node("Дедушка2")

#Я
root.add_relation(parent = b)
root.add_relation(parent = c)
root.add_relation(child= i)
z,x,v = root.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

#Брат
h.add_relation(parent = b)
h.add_relation(parent = c)
z,x,v = h.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

#Мама
b.add_relation(parent = d)
b.add_relation(parent = e)
z,x,v = b.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

#Папа
c.add_relation(parent = f)
c.add_relation(parent = g)
z,x,v = c.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

#Тетя
j.add_relation(parent = d)
j.add_relation(parent = e)
z,x,v = c.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

#Двоюродный брат
l.add_relation(parent = j)
l.add_relation(parent = k)
z,x,v = c.get_par()
print("Узел - {}, родители - {}, дети - {}".format(z,x,v))

# Вывод обхода по ширине с уровнями
result,res = breadth_first_traversal_with_levels(root)
print(result)
print(res)
# for value, level in result:
#     print(f"{value} {level}")
