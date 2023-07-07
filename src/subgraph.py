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
        self.node_cnt = 0

    def sample(self):
        to_sample = [(1, self.node_cnt, self.target_node)] # (hop, new_id, node)
        self.node_cnt += 1
        while len(to_sample) > 0:
            hop, new_id, node = to_sample.pop(0)
            node_info = NodeInfo(node)
            self.node_infos[new_id] = node_info
            node_info.set_pages(self.graph.get_pages(node))
            
            if hop > n_total_hop():
                continue
            
            n_sample = n_sample_in_hop(hop)
            sample_per_page, sampled_neighbors = self.graph.sample_n(node, n_sample)
            
            new_ids = list(range(self.node_cnt, self.node_cnt + n_sample))
            node_info.set_sample(sample_per_page, new_ids)
            
            for new_id, dst_node in zip(new_ids, sampled_neighbors):
                to_sample.append((hop + 1, new_id, dst_node))
            self.node_cnt += n_sample

    def next_node_new_ids_to_sample(self, new_id, hop):
        if hop > n_total_hop():
            return []
        node_info = self.node_infos[new_id]
        return [new_id for new_id in node_info.sampled_edges]

    def get_edge_pages(self, new_id):
        node_info = self.node_infos[new_id]
        pages = list(node_info.page2edges.keys())
        pages.sort(key=lambda x: x==node_info.pages[0], reverse=True)
        return pages

    def get_node_ids(self):
        return [self.node_infos[new_id].node.node_id for new_id in self.node_infos.keys()]

    def get_node_id(self, new_id):
        return self.node_infos[new_id].node.node_id

    def show(self):
        print("subgraph:")
        for new_id in self.node_infos:
            node_info = self.node_infos[new_id]
            node = node_info.node
            print(f"node {node.node_id}(#neighbor:{node.n_edge})")
            if node_info.sampled_edges:
                neighbor_ids = [self.node_infos[neighbor_new_id].node.node_id for neighbor_new_id in node_info.sampled_edges]
                print([f'edge({node.node_id}-{neighbor_id})' for neighbor_id in neighbor_ids])