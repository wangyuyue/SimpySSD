#!/usr/bin/env python3

import math
from queue import PriorityQueue
import argparse
import os
import sys

sys.path.append(f"{os.environ['BG_BASE_DIR']}/src")
import graph
from util import graph_params


page_size = 4096
max_n_section = 16

# header size
hd_sz = 6 # byte
# neighbor count size
nbc_sz = 2
# feature length
feat_sz = 100

def compute_sections(nr_neighbor):
    n_ppage = 1
    psec_sz = hd_sz + nbc_sz + feat_sz
    if nr_neighbor <= max_pnode:
        psec_sz += nr_neighbor * 4
        return [psec_sz]
    n_spage = math.ceil((nr_neighbor - max_pnode) / (max_snode - 1))
    sections = [page_size] * (n_ppage + n_spage - 1)
    last_snode = nr_neighbor - (max_pnode - n_spage) - (n_spage - 1) * max_snode
    sections.append(hd_sz + last_snode * 4)
    return sections

p_pages = PriorityQueue()
s_pages = PriorityQueue()

class Page:
    n_pages = 0
    def __init__(self):
        self.sections = []
        self.capacity = page_size
        Page.n_pages += 1
    def insert(self, section):
        if len(self.sections) == max_n_section:
            return False
        if self.capacity < section:
            return False
        self.sections.append(section)
        self.capacity -= section
        return True
    def __repr__(self):
        return f"used: {str(self.sections)}, left: {self.capacity}"
    
    def __lt__(self, other):
        return self.capacity >= other.capacity

def alloc_page(pages, section):
    if not pages.empty():
        old_page = pages.get()
        success = old_page.insert(section)
        pages.put(old_page)
        if success:
            return
    new_page = Page()
    new_page.insert(section)
    pages.put(new_page)

def alloc_directgraph(nr_neighbor):
    sections = compute_sections(nr_neighbor)
    alloc_page(p_pages, sections[0])
    for ssection in sections[1:]:
        alloc_page(s_pages, ssection)

def compute_efficiency(nr_neighbors):
    structure_sz = (sum(nr_neighbors) + len(nr_neighbors)) * 4
    feature_sz = len(nr_neighbors) * feat_sz
    return (page_size * Page.n_pages) / (structure_sz + feature_sz) - 1

def get_graph(name):
    if name in ['reddit', 'amazon', 'ml-1m', 'ogbn-papers100M']:
        return graph.ScaledGraph(name)
    elif name == 'Protein-PI':
        return graph.BellGraph(min_val=330, max_val=2100, hi_val=900, log_n=5.2)


def test():
    max_pnode = (page_size - (hd_sz + nbc_sz + feat_sz)) // 4
    max_snode = (page_size - hd_sz) // 4
    print(f"max #pnode in primary section: {max_pnode}")
    print(f"max #pnode in secondary section: {max_snode}")

    nr_neighbors = [972, 972, 973, 1000, 50, 28, 39, 1500]
    for nr_neighbor in nr_neighbors:
        alloc_directgraph(nr_neighbor)

    print(f"#page: {Page.n_pages}")
    print("Primary pages:")
    while not p_pages.empty():
        page = p_pages.get()
        print(page)

    print("Secondary pages:")
    while not s_pages.empty():
        page = s_pages.get()
        print(page)

    print("efficiency", compute_efficiency(nr_neighbors))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-w', '--workload')
    args = parser.parse_args()

    workload = args.workload


    feat_sz_dict = {'reddit': 1200, 'amazon': 400, 'ml-1m': 60, 'ogbn-papers100M': 64, 'Protein-PI': 512}
    graph_params['feat_sz'] = feat_sz = feat_sz_dict[workload]
    
    max_pnode = (page_size - (hd_sz + nbc_sz + feat_sz)) // 4
    max_snode = (page_size - hd_sz) // 4
    print(f"max #pnode in primary section: {max_pnode}")
    print(f"max #pnode in secondary section: {max_snode}")

    g = get_graph(workload)
    
    nr_neighbors = []
    for i in range(100000):
        node = g.sample_node()
        alloc_directgraph(node.n_edge)
        nr_neighbors.append(node.n_edge)
    
    print(f"Inflation ratio: {compute_efficiency(nr_neighbors)}")


    n_node = {'reddit': 37.3, 'amazon': 265.9, 'ml-1m': 22.2, 'ogbn-papers100M': 179.1, 'Protein-PI': 9.1}
    avg_deg = {'reddit': 1445, 'amazon': 300, 'ml-1m': 2666, 'ogbn-papers100M': 28, 'Protein-PI': 965}

    print(f"Raw size: {(n_node[workload] * 10**6) * (4 + avg_deg[workload] * 4 + feat_sz_dict[workload]) / 1024**3} GB")

# python3 src/storage_efficiency.py --workload reddit
# max #pnode in primary section: 722
# max #pnode in secondary section: 1022
# efficiency 0.9729647645615938
# python3 src/storage_efficiency.py --workload amazon
# max #pnode in primary section: 922
# max #pnode in secondary section: 1022
# efficiency 0.96087176599672
# python3 src/storage_efficiency.py --workload ml-1m
# max #pnode in primary section: 1007
# max #pnode in secondary section: 1022
# efficiency 0.9660360499118528
# python3 src/storage_efficiency.py --workload ogbn-papers100M
# max #pnode in primary section: 1006
# max #pnode in secondary section: 1022
# efficiency 0.754416836897705

# 3 byte original node index
# python3 src/storage_efficiency.py --workload Protein-PI
# max #pnode in primary section: 894
# max #pnode in secondary section: 1022
# efficiency 0.7516231582877476