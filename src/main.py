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

import argparse

def reset(gnn):
    engine.now = 0
    Cmd.cmd_id = 0
    gnn.reset_batch()
    gnn.reset_hop()

def get_graph(name):
    if name in ['reddit', 'amazon', 'ml-1m', 'ogbn-papers100M']:
        return graph.ScaledGraph(name)
    elif name == 'Protein-PI':
        return graph.BellGraph(min_val=330, max_val=2100, hi_val=900, log_n=5.2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('-w', '--workload')
    parser.add_argument('--batch_size')

    parser.add_argument('--ssd', default='ull_ssd')
    parser.add_argument('--n_core')
    
    parser.add_argument('--n_channel')
    parser.add_argument('--channel_bw')
    parser.add_argument('--n_chip')
    parser.add_argument('--page_size')

    args = parser.parse_args()

    ssd_config.read_conf_file(f'configs/ssd/{args.ssd}.cfg')
    if args.batch_size:
        app_params['batch'] = int(args.batch_size)
    if args.n_core:
        ssd_config.n_cores = int(args.n_core)
    if args.n_channel:
        ssd_config.num_channel = int(args.n_channel)
    if args.channel_bw:
        ssd_config.channel_bw_mbps = float(args.channel_bw)
    if args.n_chip:
        ssd_config.num_chip = int(args.n_chip)
    if args.page_size:
        ssd_config.pg_sz_kb = int(args.page_size)

    feat_sz = {'reddit': 1200, 'amazon': 400, 'ml-1m': 60, 'ogbn-papers100M': 64, 'Protein-PI': 512}
    graph_params['feat_sz'] = feat_sz[args.workload]

    ssd_config.dump()

    accel_config.set_accel_config('configs/accelerator/isc_tpu.cfg')
    accel_config.sim_exec_time()

    repeat = 1
    stat_dict = {}
    for i in range(repeat):
        random.seed(i)
        np.random.seed(i)
        test_graph = get_graph(args.workload)
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
            set_system_config(config_name)
            system_config.dump()
            reset(gnn)

            system = System()
            system.set_app(gnn)

            stat = Stat(n_total_hop())
            system.set_stat(stat)
            gnn.run_on(system)

            gnn.subgraphs = subgraphs
            gnn.sample_nodes(batch)
        
            while len(engine.events) > 0:
                engine.exec()
            
            stat.last_transfer_kb = last_hop_feat_sz()/1e3
            stat.total_time = engine.now

            stat_dict[system_config.name] = stat
            stat.set_accel_stat(accel_config)

        dump_chip_utilization(stat_dict)
        dump_channel_utilization(stat_dict)
        
        dump_sample_latency_breakdown(stat_dict)
        dump_overall_latency_breakdown(stat_dict)

        dump_hop_breakdown(stat_dict)
        dump_speedup(stat_dict)

        dump_energy(stat_dict)

        plot_channel_utilization(stat_dict)
        plot_chip_utilization(stat_dict)
        plot_speedup(stat_dict)