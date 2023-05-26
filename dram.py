from util import ssd_params
from sim import *
from lru import LRU

class Buffer:
    def __init__(self, vec_size, max_num):
        self.lru = LRU(max_num)
        self.sz = vec_size * max_num
    
    def lookup(self, id):
        return self.lru[id]

    def is_cached(self, id):
        return id in self.lru
    
    def insert(self, id):
        self.lru[id] = str(id)

    def print(self):
        print(self.lru.keys())


class DRAM(Sim):
    def __init__(self, system):
        self.system = system
      
        self.latency = ssd_params['dram_latency']
        self.bandwidth = ssd_params['dram_bw']
        self.capacity = ssd_params['dram_capacity']
      
        self.buffer = None
        self.next_avail_time = 0

    def __repr__(self):
        return f'SSD-DRAM'
   
    def add_buffer(self, vec_size, max_num):
        self.buffer = Buffer(vec_size, max_num)

    def delay(self, obj, func, args):
        avail_time = max(self.next_avail_time, engine.now)
        self.next_avail_time = avail_time + self.latency
        event = Event(obj, func, self.next_avail_time, args)
        engine.add(event)

        self.system.stat.start_ftl(avail_time)
        self.system.stat.end_ftl(avail_time + self.latency)
   
    def rw(self, data_sz):
        avail_time = max(self.next_avail_time, engine.now)
        self.next_avail_time = avail_time + self.latency + data_sz / self.bandwidth