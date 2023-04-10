from ssd_estimate import logger, engine, SSD, GNNAcc, Cmd
from util import *
import graph

class GNN:
    def __init__(self, graph):
        self.graph = graph
        self.subgraphs = []

        self.ssd = SSD(self)
        self.accel = GNNAcc()
        self.sync_hop = True

        self.reset()

    def reset(self):
        self.nodes_to_sample = [set() for i in range(batch_size())]
        self.wait_completion = []
    
    def process_pcie(self, data_sz):
        self.accel.add_transfer(data_sz)

    def sample_nodes(self, batch):
        for batch_i, target_node in enumerate(batch):
            self.nodes_to_sample[batch_i].add(target_node.node_id)
            subgraph =  self.subgraphs[batch_i]
            node_info = subgraph.node_infos[target_node.node_id]
            for page_id, channel_id, chip_id in node_info.pages:
                cmd = Cmd(channel_id, chip_id)
                cmd.hop = 1
                cmd.batch_i = batch_i
                self.issue(cmd)

    def issue(self, cmd):
        self.wait_completion.append(cmd)
        self.ssd.issue(cmd)

    def process(self, cmd):
        logger.debug(f"process {cmd}, pending: {self.wait_completion}")
        self.wait_completion.remove(cmd)
        
        current_hop = cmd.hop
        
        if self.sync_hop:
            print("sync hop")
            if len(self.wait_completion) == 0:
                last_hop_sampled_nodes = self.nodes_to_sample
                self.reset()
                
                if cmd.hop == n_total_hop():
                    self.accel.begin_transfer()
                    self.accel.begin_compute()
                    return

                num_sampled_nodes = sum([len(x) for x in last_hop_sampled_nodes])
                self.ssd.begin_transfer_pcie(num_sampled_nodes * 4)
                
                for batch_i, sampled_nodes in enumerate(last_hop_sampled_nodes):
                    subgraph = self.subgraphs[batch_i]
                    nodes_to_sample = self.nodes_to_sample[batch_i]

                    for sampled_node in sampled_nodes:
                        next_nodes_to_sample = subgraph.next_nodes_to_sample(sampled_node, current_hop + 1)
                        nodes_to_sample.update(next_nodes_to_sample)
                    
                    pages_to_fetch = set()
                    for next_node_to_sample in nodes_to_sample:
                        pages_to_fetch.update(subgraph.pages_to_fetch(next_node_to_sample))

                    for page in pages_to_fetch:
                        page_id, channel_id, chip_id = page
                        cmd = Cmd(channel_id, chip_id, 'read')
                        cmd.hop = current_hop + 1
                        cmd.batch_i = batch_i
                        self.issue(cmd)
            else:
                logger.debug(f"wait for other cmd in hop {current_hop}...")
        else:
            raise Exception("async not implemented")


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
        return node_info.pages

    def show(self):
        print("subgraph:")
        for node_id in self.node_infos:
            node_info = self.node_infos[node_id]
            print(f"node {node_id}({node_info.node.n_edge})")
            if node_info.sampled_edges:
                print([f'edge({node_id}-{node.node_id})' for node in node_info.sampled_edges])


if __name__ == "__main__":
    zipf_graph = graph.ZipfGraph()
    gnn = GNN(zipf_graph)
    batch = zipf_graph.get_batch(batch_size())
    
    for batch_i, target_node in enumerate(batch):
        subgraph = SubGraph(batch_i, zipf_graph, target_node)
        subgraph.sample()
        gnn.subgraphs.append(subgraph)
        subgraph.show()
    
    gnn.sample_nodes(batch)

    
    
    while len(engine.events) > 0:
        engine.exec()
