from util import *

class NodeInfo:
    def __init__(self, node):
        self.node = node
        self.page2edges = {}
        self.sampled_edges = None

    def set_pages(self, page_list):
        self.pages = page_list

    def set_sample(self, sample_per_page, sampled_edges):
        assert(sum(sample_per_page.values()) == len(sampled_edges)) 
        self.sampled_edges = sampled_edges
        offset = 0
        for ith, n_sample in sample_per_page.items():
            page = self.pages[ith]    
            self.page2edges[page] = sampled_edges[offset:offset+n_sample]
            offset += n_sample

class SubGraph:
    def __init__(self, idx, graph, target_node):
        self.idx = idx
        self.graph = graph
        self.target_node = target_node
        self.node_infos = {}

    def sample(self):
        to_sample = []
        to_sample.append((1, self.target_node)) # (hop, node)
        while len(to_sample) > 0:
            hop, node = to_sample.pop(0)
            node_info = NodeInfo(node)
            self.node_infos[node.node_id] = node_info
            node_info.set_pages(self.graph.get_pages(node))
            
            if hop > n_total_hop():
                continue
            
            n_sample = n_sample_in_hop(hop)
            sample_per_page = self.graph.sample_per_page(node, n_sample)
            sampled_edges = self.graph.sample_n(node, n_sample)
            node_info.set_sample(sample_per_page, sampled_edges)

            for dst_node in sampled_edges:
                if not dst_node.node_id in self.node_infos:
                    to_sample.append((hop + 1, dst_node))

    def next_nodes_to_sample(self, node_id, hop):
        node_info = self.node_infos[node_id]
        return [node.node_id for node in node_info.sampled_edges][:n_sample_in_hop(hop)]

    def pages_to_fetch(self, node_id):
        node_info = self.node_infos[node_id]
        pages = list(node_info.page2edges.keys())
        pages.sort(key=lambda x: x==node_info.pages[0], reverse=True)
        return pages

    def show(self):
        print("subgraph:")
        for node_id in self.node_infos:
            node_info = self.node_infos[node_id]
            print(f"node {node_id}({node_info.node.n_edge})")
            if node_info.sampled_edges:
                print([f'edge({node_id}-{node.node_id})' for node in node_info.sampled_edges])