from sim import engine
from ssd_estimate import logger, SSD, Cmd
from system import System
from util import *
import graph
from subgraph import SubGraph

class GNN:
    def __init__(self, graph, system):
        self.graph = graph
        self.subgraphs = []

        self.system = system
        self.sync_hop = True
        self.current_hop = 0

        self.reset()

    def reset(self):
        self.nodes_to_sample = [set() for i in range(batch_size())]
        self.wait_completion = []

    def sample_nodes(self, batch):
        for batch_i, target_node in enumerate(batch):
            self.nodes_to_sample[batch_i].add(target_node.node_id)
            subgraph =  self.subgraphs[batch_i]
            node_info = subgraph.node_infos[target_node.node_id]
            for page_id, channel_id, chip_id in node_info.pages:
                cmd = Cmd(channel_id, chip_id)
                cmd.hop = 0
                cmd.batch_i = batch_i
                self.issue(cmd)

    def issue(self, cmd):
        self.wait_completion.append(cmd)
        self.system.issue_cmd(cmd)

    def process(self, cmd):
        logger.debug(f"process {cmd}, pending: {self.wait_completion}")
        self.wait_completion.remove(cmd)
        
        self.current_hop = cmd.hop
        
        if self.sync_hop:
            print("sync hop")
            if len(self.wait_completion) == 0:
                last_hop_sampled_nodes = self.nodes_to_sample
                self.reset()
                
                for batch_i, sampled_nodes in enumerate(last_hop_sampled_nodes):
                    subgraph = self.subgraphs[batch_i]
                    nodes_to_sample = self.nodes_to_sample[batch_i]

                    for sampled_node in sampled_nodes:
                        next_nodes_to_sample = subgraph.next_nodes_to_sample(sampled_node, self.current_hop + 1)
                        nodes_to_sample.update(next_nodes_to_sample)

                num_sampled_nodes = sum([len(x) for x in self.nodes_to_sample])
                print(self.nodes_to_sample)
                self.system.transfer(num_sampled_nodes * 4)
                return
            else:
                logger.debug(f"wait for other cmd in hop {self.current_hop}...")
        else:
            raise Exception("async not implemented")
    
    def fetch_page(self):
        if self.current_hop == n_total_hop() - 1:
            self.system.compute()
            return
        
        for batch_i, nodes_to_sample in enumerate(self.nodes_to_sample):
            subgraph = self.subgraphs[batch_i]
            pages_to_fetch = set()
            for next_node_to_sample in nodes_to_sample:
                pages_to_fetch.update(subgraph.pages_to_fetch(next_node_to_sample))

            for page in pages_to_fetch:
                page_id, channel_id, chip_id = page
                cmd = Cmd(channel_id, chip_id, 'read')
                cmd.hop = self.current_hop + 1
                cmd.batch_i = batch_i 
                self.issue(cmd)

if __name__ == "__main__":
    system = System()
    zipf_graph = graph.ZipfGraph()
    gnn = GNN(zipf_graph, system)
    system.set_app(gnn)
    
    batch = zipf_graph.get_batch(batch_size())
    
    for i, target_node in enumerate(batch):
        subgraph = SubGraph(i, zipf_graph, target_node)
        subgraph.sample()
        gnn.subgraphs.append(subgraph)
        subgraph.show()
    
    gnn.sample_nodes(batch)
    
    while len(engine.events) > 0:
        engine.exec()
