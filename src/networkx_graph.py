import networkx as nx
import graph
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

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

if __name__ == '__main__':
    zipf_graph = graph.ZipfGraph()
    # zipf_graph.draw_node_distribution()
    # syn_graph = SyntheticGraph(zipf_graph.unit, zipf_graph.probs)
    # syn_graph.plot_edge_num_distribution()
    avg_degree = 0
    for i, prob in enumerate(zipf_graph.probs):
        zipf_graph.unit * i * prob
        avg_degree += zipf_graph.unit * i * prob
    print(avg_degree)