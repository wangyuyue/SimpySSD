from sim import engine
from ssd_estimate import logger, SSD, Cmd
from system import System
from util import batch_size, n_total_hop
from util import graph_params, config_names
import graph
import networkx_graph
from subgraph import SubGraph
import random
import numpy as np
from sys_stat import *
from ssd_config import ssd_config
from system_config import system_config, set_system_config
from accel_config import accel_config

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
        self.cmd2dst_node_new_ids = {}
        self.cmd2extcmds = {}

    def reset_hop(self):
        self.node_new_ids_to_sample = [set() for i in range(batch_size())]
        self.wait_completion = []

    def sample_node(self, batch_i, node_new_id, hop_i):
        subgraph = self.subgraphs[batch_i]
        node_info = subgraph.node_infos[node_new_id]
        pages = subgraph.get_edge_pages(node_new_id)
        if len(pages) == 0:
            print('isolated node')
            return
        
        cmds = []
        for page in pages:
            page_id, channel_id, chip_id = page
            cmd_typ = 'read'
            if system_config.flash_sample:
                cmd_typ = 'sample'
            cmd = Cmd(cmd_typ=cmd_typ, channel_id=channel_id, chip_id=chip_id, page_id=page_id)
            self.cmd2batch[cmd] = batch_i
            self.cmd2dst_node_new_ids[cmd] = {node_new_id for node_new_id in node_info.page2edges.get(page, {})}
            self.cmd2hop[cmd] = hop_i
            cmds.append(cmd)

        first_cmd = cmds[0]
        if graph_params['feat_together']:
            first_cmd.has_feat = True

        # for cmd in cmds:
        #     self.issue(cmd)
        # return
        if system_config.dram_translate:
            for cmd in cmds:
                self.issue(cmd)
        else:
            assert(system_config.flash_sample is True)
            first_cmd.has_ext = True
            self.cmd2extcmds[first_cmd] = cmds[1:]
            self.issue(first_cmd)

    def fetch_node_feat(self, node_id):
        page = self.graph.get_feat_page(self.graph.get_node(node_id))

        page_id, channel_id, chip_id = page
        cmd_typ = 'read'
        if system_config.flash_sample:
            cmd_typ = 'sample'
        cmd = Cmd(cmd_typ=cmd_typ, channel_id=channel_id, chip_id=chip_id, page_id=page_id)
        cmd.has_feat = True
        self.cmd2hop[cmd] = n_total_hop()
        self.issue(cmd)

    def sample_nodes(self, batch):
        for batch_i, target_node in enumerate(batch):
            target_node_new_id = 0
            hop = 0
            self.node_new_ids_to_sample[batch_i].add(target_node_new_id)
            self.sample_node(batch_i, target_node_new_id, hop)

    def issue(self, cmd):
        self.wait_completion.append(cmd)
        # self.system.issue_cmd(cmd)
        # return
        if system_config.channel_forward:
            self.system.issue_cmd(cmd)
        else:
            sys = self.system
            sys.ssd_dram.delay(sys, 'issue_cmd', {'cmd': cmd})

    def process(self, cmd):
        logger.debug(f"process {cmd}, pending: {self.wait_completion}")
        self.wait_completion.remove(cmd)
        
        self.current_hop = self.cmd2hop[cmd]
        if self.system.stat is not None:
            self.system.stat.end_hop(engine.now, self.cmd2hop[cmd])

        if system_config.sync_hop:
            # print("sync hop")
            if len(self.wait_completion) == 0:
                last_hop_sampled_node_new_ids = self.node_new_ids_to_sample
                self.reset_hop()
                
                for batch_i, sampled_node_new_ids in enumerate(last_hop_sampled_node_new_ids):
                    subgraph = self.subgraphs[batch_i]
                    node_new_ids_to_sample = self.node_new_ids_to_sample[batch_i]

                    for sampled_node_new_id in sampled_node_new_ids:
                        next_nodes_to_sample = subgraph.next_node_new_ids_to_sample(sampled_node_new_id, self.current_hop + 1)
                        node_new_ids_to_sample.update(next_nodes_to_sample)

                num_sampled_nodes = sum([len(x) for x in self.node_new_ids_to_sample])

                if self.current_hop < n_total_hop():
                    self.system.transfer(num_sampled_nodes * 4, 'ssd', 'host', 'node_id')
                else:
                    node_ids = set().union(*[subgraph.get_node_ids() for subgraph in self.subgraphs])
                    vec_sz = len(node_ids) * graph_params['feat_sz']

                    if accel_config.accel_loc == 'pcie':
                        if graph_params['feat_in_mem'] is True:
                            self.system.transfer(vec_sz, 'host', 'dnn_accel', 'feat')
                        else:
                            self.system.transfer(vec_sz, 'ssd', 'host', 'feat')
                    else:
                        if graph_params['feat_in_mem'] is True:
                            self.system.transfer(vec_sz, 'host', 'ssd', 'feat')
                        else:
                            self.system.check_compute()                            
                return
            else:
                logger.debug(f"wait for other cmd in hop {self.current_hop}...")
        else:
            assert(graph_params['feat_together'] is True)
            if self.current_hop < n_total_hop():
                batch_i = self.cmd2batch[cmd]
                subgraph = self.subgraphs[batch_i]
                self.node_new_ids_to_sample[batch_i] = self.cmd2dst_node_new_ids[cmd]
                self.fetch_page_async(batch_i, self.node_new_ids_to_sample[batch_i])
                self.node_new_ids_to_sample[batch_i] = set()
            else:
                self.system.check_compute()
    
    def get_pcie_notified(self, pcie_args):
        if pcie_args['data_type'] == 'node_id':
            self.fetch_page_sync()
        else:
            if pcie_args['src'] == 'ssd' and pcie_args['dst'] == 'host' and pcie_args['data_type'] == 'feat':
                self.system.transfer(pcie_args['data_sz'], 'host', 'dnn_accel', 'feat')
            elif pcie_args['src'] == 'host' and pcie_args['dst'] == 'ssd' and pcie_args['data_type'] == 'feat':
                self.system.check_compute()
            elif pcie_args['src'] == 'host' and pcie_args['dst'] == 'dnn_accel' and pcie_args['data_type'] == 'feat':
                self.system.check_compute()
            else:
                raise Exception(f"unknown pcie operation")

    def fetch_page_sync(self):
        for batch_i, node_new_ids_to_sample in enumerate(self.node_new_ids_to_sample):
            self.fetch_page_async(batch_i, node_new_ids_to_sample)

        if graph_params['feat_together'] is False:
            if self.current_hop == n_total_hop() - 1:
                node_ids = set().union(*[subgraph.get_node_ids() for subgraph in self.subgraphs])
                for node_id in node_ids:
                    self.fetch_node_feat(node_id)

    def fetch_page_async(self, batch_i, node_new_ids_to_sample):
        if self.current_hop < n_total_hop() - 1:
            for next_node_new_id_to_sample in node_new_ids_to_sample:
                self.sample_node(batch_i, next_node_new_id_to_sample, self.current_hop + 1)
        elif self.current_hop == n_total_hop() - 1:
            if graph_params['feat_together'] is True:
            # when feature is stored together, we only need to fetch the last hop's features separately
                for node_new_id in node_new_ids_to_sample:
                    node_id = self.subgraphs[batch_i].get_node_id(node_new_id)
                    self.fetch_node_feat(node_id)
        else:
            raise Exception(f"invalid hop {self.current_hop}")

def reset(gnn):
    engine.now = 0
    Cmd.cmd_id = 0
    gnn.reset_batch()
    gnn.reset_hop()

if __name__ == "__main__":
    ssd_config.read_conf_file('configs/ssd/traditional_ssd.cfg')
    ssd_config.dump()
    repeat = 1
    repeat_test = []
    stat_dict = {}
    for i in range(repeat):
        random.seed(i)
        np.random.seed(i)
        zipf_graph = graph.ZipfGraph()
        # zipf_graph = networkx_graph.get_nxgraph()
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
        
        for config_name in config_names:
        # for config in configs:
            # print(f"config: {config['name']}")
            set_system_config(config_name)
            system_config.dump()
            reset(gnn)
            # system_params.update(config)

            system = System()
            system.set_app(gnn)

            system.set_stat(Stat(n_total_hop()))
            gnn.run_on(system)

            gnn.subgraphs = subgraphs
            gnn.sample_nodes(batch)
        
            while len(engine.events) > 0:
                engine.exec()
            
            system.stat.total_time = engine.now

            from stat_plot import *
            # stat_dict[config['name']] = system.stat
            stat_dict[system_config.name] = system.stat
        print(stat_dict)
        plot_sample_latency_breakdown(stat_dict)
        plot_chip_utilization(stat_dict)
        plot_channel_utilization(stat_dict)
        plot_hop_breakdown(stat_dict)
        plot_overall_latency_breakdown(stat_dict)
        plot_speedup(stat_dict)