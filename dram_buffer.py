from lru import LRU

class Buffer:
    def __init__(self, vec_size, max_num):
       self.lru = LRU(max_num)
    
    def lookup(self, id):
       return self.lru[id]

    def is_cached(self, id):
       return id in self.lru
    
    def insert(self, id):
       self.lru[id] = str(id)

    def print(self):
       print(self.lru.keys())