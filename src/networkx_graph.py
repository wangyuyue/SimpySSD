import networkx as nx
import graph
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from util import *

class NxGraph(graph.Graph):
    def __init__(self, nx_graph):
        super().__init__()
        self.nx_graph = nx_graph
        self.node2pages = {}
        self.page_id = 0

    def get_nx_graph(self):
        return self.nx_graph

    def get_random_page(self):
        self.page_id += 1
        return (self.page_id, rand_channel(), rand_chip())
    
    def get_random_node_id(self):
        # get a node from nx_graph
        node_id = random.choice(list(self.nx_graph.nodes()))

    def set_pages(self, node):
        # node id 4(byte) is enough for million-nodes-scale graph
        sz = node.n_edge * 4
        if self.feat_together:
            sz += self.feat_sz
        n_page = math.ceil(sz / (1e3 * ssd_config.pg_sz_kb))
        self.node2pages[node.node_id] = [self.get_random_page() for i in range(n_page)]

    def get_pages(self, node):
        if not node.node_id in self.node2pages:
            self.set_pages(node)
        return self.node2pages[node.node_id]

    def get_node(self, node_id):
        n_neighbors = len(list(self.nx_graph.neighbors(node_id)))
        return graph.Node(node_id, n_neighbors)
    
    def get_feat_page(self, node):
        if self.feat_together:
            return self.get_pages(node)[0]
        node_id = node.node_id
        if not node_id in self.node2feat_page:
            self.node2feat_page[node_id] = self.get_random_page()
        return self.node2feat_page[node_id]
    
    def sample_per_page(self, node_relative_id_list):
        offset = 0
        if self.feat_together:
            offset += self.feat_sz
        sample_per_page = {}
        for node_relative_id in node_relative_id_list:
            page_relative_id = math.floor((offset + (node_relative_id + 1) * 4) / (1e3 * ssd_config.pg_sz_kb))
            sample_per_page[page_relative_id] = sample_per_page.get(page_relative_id, 0) + 1
        return sample_per_page

    def sample_n(self, node, n):
        neighbor_list = list(self.nx_graph.neighbors(node.node_id))
        
        sample_indexes = random.sample(range(len(neighbor_list)), n)
        sampled_neighbors = [self.get_node(neighbor_list[i]) for i in sample_indexes]
        sample_per_page = self.sample_per_page(sample_indexes)
        return sample_per_page, sampled_neighbors

    def get_batch(self, batch_size):
        nodes = []
        node_ids = random.sample(self.nx_graph.nodes(), batch_size)
        n_neighbors = [len(list(self.nx_graph.neighbors(node_id))) for node_id in node_ids]
        return [graph.Node(node_id, n_neighbor) for node_id, n_neighbor in zip(node_ids, n_neighbors)]
    

class SyntheticGraph(graph.Graph):
    def __init__(self, edge_num_unit, edge_num_prob_list):
        super().__init__()
        w_list = np.array([])
        for i, prob in enumerate(edge_num_prob_list):
            edge_num = (i + 0.5) * edge_num_unit
            node_num = int(self.n_node * prob)
            if node_num == 0:
                continue
            print(node_num, edge_num)
            w_list = np.concatenate((w_list, np.full(node_num, edge_num)))
            print(w_list.shape)
        self.nx_graph = nx.expected_degree_graph(w_list)

    def plot_edge_num_distribution(self):
        sns.distplot([self.nx_graph.degree[i] for i in self.nx_graph.nodes], kde=False)
        plt.savefig('edge_num_distribution.png')


def get_nxgraph():
    zipf_graph = graph.ZipfGraph()
    zipf_graph.draw_node_distribution()
    syn_graph = SyntheticGraph(zipf_graph.unit, zipf_graph.probs)
    return NxGraph(syn_graph.nx_graph)

if __name__ == '__main__':
    zipf_graph = graph.ZipfGraph()
    zipf_graph.draw_node_distribution()
    syn_graph = SyntheticGraph(zipf_graph.unit, zipf_graph.probs)
    # syn_graph.plot_edge_num_distribution()
    
    # avg_degree = 0
    # for i, prob in enumerate(zipf_graph.probs):
    #     avg_degree += zipf_graph.unit * i * prob
    # print(avg_degree)
