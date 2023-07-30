import random
import numpy as np

from sim import engine
from ssd_estimate import Cmd
from system import System
from util import batch_size, n_total_hop, last_hop_feat_sz
from util import config_names

import graph
import networkx_graph
from subgraph import SubGraph

from system_config import system_config, set_system_config
from ssd_config import ssd_config
from accel_config import accel_config

from statistics.energy_estimate import *
from statistics.sys_stat import *
from statistics.dump import *
from statistics.plot import *

from gnn import GNN

def reset(gnn):
    engine.now = 0
    Cmd.cmd_id = 0
    gnn.reset_batch()
    gnn.reset_hop()

if __name__ == "__main__":
    ssd_config.read_conf_file('configs/ssd/ull_ssd.cfg')
    ssd_config.dump()

    accel_config.set_accel_config('configs/accelerator/pcie_tpu.cfg')
    accel_config.sim_exec_time()
    accel_config.get_statistics()

    repeat = 1
    repeat_test = []
    stat_dict = {}
    for i in range(repeat):
        random.seed(i)
        np.random.seed(i)
        # test_graph = graph.ZipfGraph()
        test_graph = graph.BellGraph(min_val=330, max_val=2100, hi_val=900, log_n=5.2)
        # test_graph = graph.ScaledGraph('ogbn-papers100M')
        # test_graph = networkx_graph.get_nxgraph()
        gnn = GNN(test_graph)

        batch = test_graph.get_batch(batch_size())
    
        subgraphs = []
        for i, target_node in enumerate(batch):
            subgraph = SubGraph(i, test_graph, target_node)
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

            system.set_stat(Stat({"num_hop":n_total_hop(), "last_transfer_kb": last_hop_feat_sz()/1e3}))
            gnn.run_on(system)

            gnn.subgraphs = subgraphs
            gnn.sample_nodes(batch)
        
            while len(engine.events) > 0:
                engine.exec()
            
            system.stat.total_time = engine.now

            stat_dict[system_config.name] = system.stat
            system.stat.set_accel_stat(accel_config)
            
        dump_energy(stat_dict)
        # plot_sample_latency_breakdown(stat_dict)
        # plot_chip_utilization(stat_dict)
        # plot_channel_utilization(stat_dict)
        # plot_hop_breakdown(stat_dict)
        # plot_overall_latency_breakdown(stat_dict)
        # plot_speedup(stat_dict)

        # dump_hop_breakdown(stat_dict)