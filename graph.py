import math
import random
import numpy as np
import matplotlib.pyplot as plt
from util import *

class Graph:
    def __init__(self):
        self.reset()
    def reset(self):
        self.feat_sz = graph_params['feat_sz']
        self.n_node = graph_params['n_node']
        self.feat_together = graph_params['feat_together']

class Node:
    def __init__(self, node_id, n_edge):
        self.node_id = node_id
        self.n_edge = n_edge

class RandomGraph(Graph):
    def __init__(self):
        super().__init__()
        self.page_id = 0
        self.node_id = 0
        self.node2pages = {}

    def get_random_page(self):
        self.page_id += 1
        return (self.page_id, rand_channel(), rand_chip())
    
    def get_random_node_id(self):
        self.node_id += 1
        return self.node_id

    def set_pages(self, node):
        # node id 4(byte) is enough for million-nodes-scale graph
        sz = node.n_edge * 4
        if self.feat_together:
            sz += self.feat_sz
        n_page = math.ceil(sz / (1e3 * ssd_params['pg_sz']))
        self.node2pages[node.node_id] = [self.get_random_page() for i in range(n_page)]

    def get_pages(self, node):
        if not node.node_id in self.node2pages:
            self.set_pages(node)
        return self.node2pages[node.node_id]

    def get_feat_page(self, node):
        if self.feat_together:
            return self.get_pages(node)[0]
        return self.get_random_page()

    def sample_per_page(self, node, n):
        node_id_list = random.sample(range(node.n_edge), n)
        offset = 0
        if self.feat_together:
            offset += self.feat_sz
        sample_per_page = {}
        for node_id in node_id_list:
            page_id = math.floor((offset + (node_id + 1) * 4) / (1e3 * ssd_params['pg_sz']))
            sample_per_page[page_id] = sample_per_page.get(page_id, 0) + 1
        return sample_per_page

    def sample_n(self, node, n):
        return [self.sample_edge() for i in range(n)]

    def get_batch(self, batch_size):
        return [self.sample_node() for i in range(batch_size)]

    def sample_node(self):
        node_id = self.get_random_node_id()
        slot_id = np.random.choice(np.arange(self.slot), p=self.probs)
        lval = slot_id * self.unit
        rval = lval + self.unit
        n_edge = random.randrange(lval, rval)
        return Node(node_id, n_edge)

    def sample_edge(self):
        node_id = self.get_random_node_id()
        slot_id = np.random.choice(np.arange(self.slot), p=self.edge_probs)
        lval = slot_id * self.unit
        rval = lval + self.unit
        n_edge = random.randrange(lval, rval)
        return Node(node_id, n_edge)
    
    def draw_node_distribution(self, n_sample = 200000):
        samples = np.array([self.sample_node().n_edge // self.unit for i in range(n_sample)])
        count = np.bincount(samples)
        k = np.arange(1, samples.max() + 1)
        plt.figure()
        plt.bar(k, count[1:], alpha=0.5, label='sample count')
        plt.semilogy()
        plt.grid(alpha=0.4)
        plt.savefig(f'{type(self).__name__}_node.png')

    def draw_edge_distribution(self, n_sample = 200000):
        samples = np.array([self.sample_edge().n_edge // self.unit for i in range(n_sample)])
        count = np.bincount(samples)
        k = np.arange(1, samples.max() + 1)
        plt.figure()
        plt.bar(k, count[1:], alpha=0.5, label='sample count')
        plt.semilogy()
        plt.grid(alpha=0.4)
        plt.savefig(f'{type(self).__name__}_edge.png')


class BellGraph(RandomGraph):
    def __init__(self, min_val, max_val, hi_val, log_n):
        super().__init__()
        self.min_val = min_val
        self.max_val = max_val
        self.hi_val = hi_val
        self.log_n = log_n
        self.unit = 10
        self.slot = math.ceil(self.max_val / self.unit)
        distribution = []
        for i in range(self.slot):
            val = i * self.unit
            if val < self.min_val:
                log_ni = 0
            elif self.min_val <= val and val < self.hi_val:
                log_ni = self.log_n * (1 - math.pow((val - hi_val)/(min_val - hi_val), 2))
            elif self.hi_val <= val and val <= self.max_val:
                log_ni = self.log_n * (1 - math.pow((val - hi_val)/(max_val - hi_val), 2))
            distribution.append(pow(10, log_ni))
        _sum = sum(distribution)
        self.probs = [x/_sum for x in distribution]

        _edge = [p * ((i + .5) * self.unit) for i, p in enumerate(self.probs)]
        _edge_sum = sum(_edge)
        self.edge_probs = [x/_edge_sum for x in _edge]


class ZipfGraph(RandomGraph):
    def __init__(self, shape = 2.0):
        super().__init__()
        self.shape = shape
        self.unit = 200
        self.slot = 100
        samples = np.random.zipf(self.shape, 200000)
        distribution = np.bincount(samples[samples < self.slot])
        _sum = distribution.sum()
        self.probs = [x/_sum for x in distribution]
        
        _edge = [p * ((i + .5) * self.unit) for i, p in enumerate(self.probs)]
        _edge_sum = sum(_edge)
        self.edge_probs = [x/_edge_sum for x in _edge]


if __name__ == '__main__':
    zipf = ZipfGraph()

    zipf.draw_edge_distribution()

    bell = BellGraph(min_val=60, max_val=1100, hi_val=300, log_n=4.5)
    bell.draw_node_distribution()