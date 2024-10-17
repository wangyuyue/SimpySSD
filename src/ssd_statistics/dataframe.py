import pandas as pd
from ssd_config import ssd_config
from .energy_estimate import *
from .cc_latency import *

def overall_latency_pd(stat_dict):
    breakdown_list = []
    
    cc_breakdown = cc_latency_breakdown(stat_dict['BG-1'])
    cc_breakdown['config'] = 'CC'
    breakdown_list.append(cc_breakdown)
    for label, stat in stat_dict.items():
        breakdown = {}
        breakdown['config'] = label

        direction = 'ssd->host'
        if direction in stat.pcie_end_time:
            breakdown['pcie'] = sum(stat.pcie_end_time[direction]) - sum(stat.pcie_start_time[direction])
        else:
            breakdown['pcie'] = 0
        breakdown['host'] = stat.total_host_delay
        if breakdown['pcie'] > 0:
            breakdown['flash'] = sum(stat.hop_end_time) - sum(stat.hop_start_time)
        else:
            breakdown['flash'] = stat.hop_end_time[-1] - stat.hop_start_time[0]
        breakdown['dnn'] = sum(stat.dnn_end_time) - sum(stat.dnn_start_time)
        
        breakdown_list.append(breakdown)
    df = pd.DataFrame(breakdown_list)
    return df

def sample_latency_pd(stat_dict):
    breakdown_list = []
    configs = []
    for label, stat in stat_dict.items():
        configs.append(label)
        cmd_stats = stat.cmd_stat
        wait_time1 = 0
        read_time = ssd_config.read_latency_us
        sample_time = 1
        wait_time2 = 0
        transfer_time = 0
        for cmd_stat in cmd_stats.values():
            wait_time1 += cmd_stat.time['read_begin'] - cmd_stat.time['issue']
            wait_time2 += cmd_stat.time['transfer_begin'] - (cmd_stat.time['read_begin'] + read_time + sample_time)
            transfer_time += cmd_stat.time['transfer_end'] - cmd_stat.time['transfer_begin']
        wait_time1 /= len(cmd_stats)
        wait_time2 /= len(cmd_stats)
        transfer_time /= len(cmd_stats)
        breakdown = {'wait_before_flash': wait_time1, 'flash_read': read_time, 'sample': sample_time, \
           'wait_after_flash': wait_time2, 'channel_transfer': transfer_time}
        breakdown['config'] = label
        breakdown_list.append(breakdown)

    df = pd.DataFrame(breakdown_list, index=configs)
    return df

def speedup_dict(stat_dict):
    dic = {'config': [], 'latency': []}
    
    dic['config'].append('CC')
    dic['latency'].append(cc_total_latency(stat_dict['BG-1']))

    for label, stat in stat_dict.items():
        dic['config'].append(label)
        dic['latency'].append(max(stat.dnn_start_time[-1], stat.dnn_end_time[-1]-stat.dnn_start_time[-1]))
    
    baseline = max(dic['latency'])
    dic['speedup'] = [baseline/lat for lat in dic['latency']]
    return dic

# def energy_breakdown_dict(stat_dict):
    # breakdown_list = []
    # configs = []
    # for label, stat in stat_dict.items():
    #     configs.append(label)
    #     breakdown = {}
    #     breakdown['config'] = label
    #     breakdown['dnn'] = dnn_energy(stat)
    #     breakdown['flash'] = flash_energy(stat)
    #     breakdown['pcie'] = pcie_energy(stat)
    #     breakdown['host'] = host_energy(stat)
    #     breakdown_list.append(breakdown)
