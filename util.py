import random
import math

ssd_params = {'channel bw': 800, # MB/s
         'read_latency': 3, # us
         'write_latency': 100, # us
         'pg_sz': 8, # KB 
        'num_chip':8, 'num_channel':8,
        'pcie_bw': 1e3 # MB/s
        }

graph_params = {'feat': 50, 'n_node': 2e20, 'feat_in_mem': False,'feat_together': True}

app_params = {'batch': 1, 'sample_per_hop': [2, 2]}

def rand_chip():
    return random.randrange(ssd_params['num_chip'])

def rand_channel():
    return random.randrange(ssd_params['num_channel'])

def n_total_hop():
    return len(app_params['sample_per_hop'])

def n_sample_in_hop(hop):
    return app_params['sample_per_hop'][hop - 1]

def total_sample():
    sample_list = [1]
    for sample in app_params['sample_per_hop']:
        last_sample = sample_list[-1]
        sample_list.append(last_sample * sample)
    return sum(sample_list) 

def batch_size():
    return app_params['batch']

def page_align_sz(data_sz):
    pg_sz = ssd_params['pg_sz'] * 1e3
    return math.ceil(data_sz / pg_sz) * pg_sz