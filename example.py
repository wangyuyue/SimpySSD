import os

import torch
from torch_geometric.datasets import TUDataset, Reddit, AmazonProducts, MovieLens1M
from ogb.nodeproppred import PygNodePropPredDataset

from torch_geometric.utils import sort_edge_index, degree
from torch_geometric.data import HeteroData

import seaborn as sns
import matplotlib.pyplot as plt

data_dir = "/users/glacier/work/pg/dataset"
deg_dir = "/users/glacier/work/pg/deg_file"

def example_dataset():
    return TUDataset(root='/tmp/ENZYMES', name='ENZYMES')

def reddit():
    dataset = Reddit(root=f"{data_dir}/reddit")
    dataset.name = "reddit"
    return dataset

def amazon():
    dataset = AmazonProducts(root=f"{data_dir}/amazon")
    dataset.name = "amazon"
    return dataset

def movieLens():
    dataset = MovieLens1M(root=f"{data_dir}/ml-1m")
    dataset.name = "ml-1m"
    return dataset

def ogb():
    dataset = PygNodePropPredDataset(name = "ogbn-papers100M", root = f'{data_dir}/ogbg-molhiv')
    return dataset

def print_dataset_info(dataset):
    print(f"num_graph:{len(dataset)}, num_classes:{dataset.num_classes}, num_node_features:{dataset.num_node_features}")
    

load_funcs = {'reddit': reddit, 'amazon': amazon, 'ml-1m': movieLens, 'ogbn-papers100M': ogb}

def load_data(name):
    dataset = load_funcs[name]()
    data = dataset[0]
    return data

def print_data_info(data):
    if isinstance(data, HeteroData):
        n_node = 0
        for n_type in data.node_types:
            n_node += data[n_type].num_nodes
            print(n_type, data[n_type].num_nodes)
        n_edge = 0
        for e_type in data.edge_types:
            n_edge += data[e_type].num_edges
            print(e_type, data[e_type].num_edges)
        print(f"num_node:{n_node}, num_edge:{n_edge}, average degree:{n_edge/n_node}")
    else:
        n_node = data.x.shape[0]
        n_edge = data.edge_index.shape[1]
        print(f"num_node:{n_node}, num_edge:{n_edge}, average degree:{n_edge/n_node}")

def get_degree_from_data(name, data):
    if isinstance(data, HeteroData):
        degs = {}
        for e_type in data.edge_types:
            src_type = e_type[0]
            deg = degree(data[e_type].edge_index[0], data[src_type].num_nodes)
            if src_type in degs:
                degs[src_type] = torch.add(deg, degs[src_type])
            else:
                degs[src_type] = deg
        deg = torch.cat(list(degs.values()))
    else:
        deg = degree(data.edge_index[0], data.num_nodes)

    deg_file = f"{deg_dir}/{name}.pt"
    if not os.path.exists(deg_file):
        torch.save(deg, deg_file)

    return deg

def draw_deg_hist(name, deg):
    plt.figure()
    sns.histplot(data=deg, bins=100, log_scale=(False, True))
    plt.savefig(f"{name}.png")



def load_deg_file(name):
    return torch.load(f"{deg_dir}/{name}.pt")

names = ['reddit', 'amazon', 'ml-1m', 'ogbn-papers100M']

scaled_degree = [1445, 300, 2666, 28]
# reddit: 37.3M, 53.9B -> 1445
# amazon 265.9M, 9.5B -> 35, use 300, b/c originally 168
# movieliens: 22.2M, 59.2B -> 2666
# ogbn100M: 179.1M, 5.0B -> 28

def scale_degree(degs):
    avg_deg = torch.sum(degs) / len(degs)
    degs *= 1.3
    degs += (scaled_degree[names.index(name)] - 1.3 * avg_deg)

    return degs

def store_distribution(name, degs):
    scaled_dis_dir = "/users/glacier/work/pg/scaled_distribution"
    
    node_distribution = torch.bincount((degs/100).long())
    node_distribution = node_distribution/torch.sum(node_distribution)

    edge_distribution = torch.bincount((degs/100).long(), degs.long())
    edge_distribution = edge_distribution/torch.sum(edge_distribution)

    if not os.path.exists(f"{scaled_dis_dir}/{name}"):
        os.mkdir(f"{scaled_dis_dir}/{name}")
    torch.save(node_distribution, f"{scaled_dis_dir}/{name}/node_dis.pt")

    torch.save(edge_distribution, f"{scaled_dis_dir}/{name}/edge_dis.pt")

    return node_distribution, edge_distribution

def draw_distribution(name, node_distribution, edge_distribution):
    plt.figure()
    sns.lineplot(x = list(range(len(node_distribution))), y = node_distribution)
    sns.lineplot(x = list(range(len(edge_distribution))), y = edge_distribution)
    plt.yscale("log")
    plt.savefig(f"{name}_sample_distribution.png")

for name in names:
    # data = load_data(name)
    # get_degree_from_data(name, data)
    degs = load_deg_file(name)
    # draw_deg_hist(name, deg)
    scaled_degs = scale_degree(degs)
    print(torch.sum(scaled_degs) / len(scaled_degs))

    node_distribution, edge_distribution = store_distribution(name, scaled_degs)
    draw_distribution(name, node_distribution, edge_distribution)

    

    

# https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.data.HeteroData.html
# https://pytorch-geometric.readthedocs.io/en/latest/tutorial/heterogeneous.html
# https://github.com/snap-stanford/ogb
# https://pytorch-geometric.readthedocs.io/en/latest/cheatsheet/data_cheatsheet.html
# https://dl.acm.org/doi/pdf/10.1145/3470496.3527391