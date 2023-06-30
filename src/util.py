import random
import math
from ssd_config import ssd_config

config_names = ['smartSage', 'smartSage_async', 'sample_sync', 'sample_async', 'sample_async_forward']

graph_params = {'feat_sz': 500, 'n_node': 1e6, 'feat_in_mem': False,'feat_together': True}

app_params = {'batch': 512, 'sample_per_hop': [3, 3, 3], 'hidden_dim':128, 'output_dim':10}

def rand_chip():
    return random.randrange(ssd_config.num_chip)

def rand_channel():
    return random.randrange(ssd_config.num_channel)

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
    pg_sz = ssd_config.pg_sz_kb * 1e3
    return math.ceil(data_sz / pg_sz) * pg_sz