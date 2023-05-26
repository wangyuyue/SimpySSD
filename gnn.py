from sim import engine
from ssd_estimate import logger, SSD, Cmd
from system import System
from util import *
import graph
from subgraph import SubGraph
import random
import numpy as np
from sys_stat import *

class GNN:
    def __init__(self, graph):
        self.graph = graph

        self.reset_batch()

        self.reset_hop()
    
    def run_on(self, system):
        self.system = system

    def reset_batch(self):
        self.subgraphs = []
        self.current_hop = 0
        self.cmd2batch = {}
        self.cmd2hop = {}
        self.cmd2dst_node = {}
        self.cmd2extcmds = {}

    def reset_hop(self):
        self.nodes_to_sample = [set() for i in range(batch_size())]
        self.wait_completion = []

    def sample_node(self, batch_i, node_id, hop_i):
        subgraph = self.subgraphs[batch_i]
        node_info = subgraph.node_infos[node_id]
        pages = subgraph.pages_to_fetch(node_id)
        cmds = []
        for page in pages:
            page_id, channel_id, chip_id = page
            cmd_typ = 'read'
            if system_params['flash_sample']:
                cmd_typ = 'sample'
            cmd = Cmd(cmd_typ=cmd_typ, channel_id=channel_id, chip_id=chip_id, page_id=page_id)
            self.cmd2batch[cmd] = batch_i
            self.cmd2dst_node[cmd] = {node.node_id for node in node_info.page2edges.get(page, {})}
            self.cmd2hop[cmd] = hop_i
            cmds.append(cmd)
        
        first_cmd = cmds[0]
        if graph_params['feat_together']:
            first_cmd.has_feat = True

        # for cmd in cmds:
        #     self.issue(cmd)
        # return
        if system_params['dram_translate']:
            for cmd in cmds:
                self.issue(cmd)
        else:
            assert(system_params['flash_sample'] == True)
            first_cmd.has_ext = True
            self.cmd2extcmds[first_cmd] = cmds[1:]
            self.issue(first_cmd)

    def sample_nodes(self, batch):
        for batch_i, target_node in enumerate(batch):
            self.nodes_to_sample[batch_i].add(target_node.node_id)
            self.sample_node(batch_i, target_node.node_id, 0)

    def issue(self, cmd):
        self.wait_completion.append(cmd)
        # self.system.issue_cmd(cmd)
        # return
        if system_params['channel_forward']:
            self.system.issue_cmd(cmd)
        else:
            sys = self.system
            sys.ssd_dram.delay(sys, 'issue_cmd', {'cmd': cmd})

    def process(self, cmd):
        logger.debug(f"process {cmd}, pending: {self.wait_completion}")
        self.wait_completion.remove(cmd)
        
        self.current_hop = self.cmd2hop[cmd]
        
        self.system.stat.end_hop(engine.now, self.cmd2hop[cmd])

        if system_params['sync_hop']:
            # print("sync hop")
            if len(self.wait_completion) == 0:
                last_hop_sampled_nodes = self.nodes_to_sample
                self.reset_hop()
                
                for batch_i, sampled_nodes in enumerate(last_hop_sampled_nodes):
                    subgraph = self.subgraphs[batch_i]
                    nodes_to_sample = self.nodes_to_sample[batch_i]

                    for sampled_node in sampled_nodes:
                        next_nodes_to_sample = subgraph.next_nodes_to_sample(sampled_node, self.current_hop + 1)
                        nodes_to_sample.update(next_nodes_to_sample)

                num_sampled_nodes = sum([len(x) for x in self.nodes_to_sample])

                self.system.transfer(num_sampled_nodes * 4, 'ssd', 'host')
                return
            else:
                logger.debug(f"wait for other cmd in hop {self.current_hop}...")
        else:
            batch_i = self.cmd2batch[cmd]
            subgraph = self.subgraphs[batch_i]
            self.nodes_to_sample[batch_i] = self.cmd2dst_node[cmd]
            self.fetch_page_async(batch_i, self.nodes_to_sample[batch_i])
            self.nodes_to_sample[batch_i] = set()
    
    def fetch_page_sync(self):
        if self.current_hop == n_total_hop() - 1:
            self.system.check_compute()
            return
        
        for batch_i, nodes_to_sample in enumerate(self.nodes_to_sample):
            self.fetch_page_async(batch_i, nodes_to_sample)

    def fetch_page_async(self, batch_i, nodes_to_sample):
        if self.current_hop == n_total_hop() - 1:
            self.system.check_compute()
            return

        subgraph = self.subgraphs[batch_i]

        for next_node_to_sample in nodes_to_sample:
            self.sample_node(batch_i, next_node_to_sample, self.current_hop + 1)


def reset(gnn):
    engine.now = 0
    Cmd.cmd_id = 0
    gnn.reset_batch()
    gnn.reset_hop()

if __name__ == "__main__":
    repeat = 1
    repeat_test = []
    stat_dict = {}
    for i in range(repeat):
        random.seed(i)
        np.random.seed(i)
        zipf_graph = graph.ZipfGraph()
        gnn = GNN(zipf_graph)

        batch = zipf_graph.get_batch(batch_size())
    
        subgraphs = []
        for i, target_node in enumerate(batch):
            subgraph = SubGraph(i, zipf_graph, target_node)
            subgraph.sample()
            subgraphs.append(subgraph)
            # subgraph.show()
            # for node_i, node_info in subgraph.node_infos.items():
            #     print(node_i, node_info.pages)
        
        latency = []
        for config in configs:
            print(f"config: {config['name']}")
            reset(gnn)
            system_params.update(config)

            system = System()
            system.set_app(gnn)

            system.set_stat(Stat(n_total_hop()))
            gnn.run_on(system)

            gnn.subgraphs = subgraphs
            gnn.sample_nodes(batch)
        
            while len(engine.events) > 0:
                engine.exec()
            
            system.stat.total_time = engine.now
            latency.append(engine.now)

            from stat_plot import *
            stat_dict[config['name']] = system.stat
        
        print(stat_dict)
        plot_sample_latency_breakdown(stat_dict)
        plot_chip_utilization(stat_dict)
        plot_channel_utilization(stat_dict)
        plot_hop_breakdown(stat_dict)
        plot_overall_latency_breakdown(stat_dict)
        plot_speedup(stat_dict)
        
    #     repeat_test.append(latency)

    # latency = [sum(t)/len(t) for t in zip(*repeat_test)]

    # import seaborn as sns
    # dic = {}
    # dic['name'] = [config['name'] for config in configs]
    # dic['latency'] = [latency[0]/lat for lat in latency]
    # plot = sns.barplot(x='name', y='latency', data=dic)
    # plot.set(xlabel='config', ylabel='speedup')
    # plot.get_figure().savefig(f'speedup_feat{graph_params["feat_sz"]}_batch_{app_params["batch"]}_hop_{"_".join([str(i) for i in app_params["sample_per_hop"]])}.png')