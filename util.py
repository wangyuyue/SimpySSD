import random
import math

ssd_params = {'channel_bw': 800, # MB/s
         'read_latency': 3, # us
         'write_latency': 30, # us
         'pg_sz': 4, # KB 
         'num_chip':8,
         'num_channel':32,
         'dram_bw': 16e3, #MB/s
         'dram_latency': 0.2 #us
        }

system_params = {
    'pcie_bw': 4e3, # MB/s
    'accel_loc': 'pcie',
    'host_side_delay': 3, # us
}

smartSage_config = {
    'name': 'smartSage',
    'flash_sample': False,
    'channel_forward': False,
    'sync_hop': True,
    'sync_host': True,
    'dram_node2pages_map': True
}

smartSage_async_config = {
    'name': 'smartSage_async',
    'flash_sample': False,
    'channel_forward': False,
    'sync_hop': False,
    'sync_host': False,
    'dram_node2pages_map': True
}

sample_sync_config = {
    'name': 'sample_sync',
    'flash_sample': True,
    'channel_forward': False,
    'sync_hop': True,
    'sync_host': False,
    'dram_node2pages_map': True
}

sample_async_config = {
    'name': 'sample_async',
    'flash_sample': True,
    'channel_forward': False,
    'sync_hop': False,
    'sync_host': False,
    'dram_node2pages_map': True
}

configs = [smartSage_config, smartSage_async_config, sample_sync_config, sample_async_config]

graph_params = {'feat_sz': 500, 'n_node': 2e20, 'feat_in_mem': False,'feat_together': True}

app_params = {'batch': 128, 'sample_per_hop': [3, 3, 3, 3]}

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