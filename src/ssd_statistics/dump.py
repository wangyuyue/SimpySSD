import csv
from .dataframe import *
from .series_process import smooth_timeline

def dump_chip_utilization(stat_dict):
    with open('chip_utilization.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['config', 'time (us)', 'chip utilization'])
        for config, stat in stat_dict.items():
            smooth = 2.5
            if config in ["BG-1", "BG-DG"]:
                smooth = 5
            stat.chip_busy_time, stat.chip_busy_n = smooth_timeline(stat.chip_busy_time, stat.chip_busy_n, smooth)
            for x, y in zip(stat.chip_busy_time, stat.chip_busy_n):
                writer.writerow([config, x, y])

def dump_channel_utilization(stat_dict):
    with open('channel_utilization.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['config', 'time (us)', 'channel utilization'])
        for config, stat in stat_dict.items():
            smooth = 2.5
            if config in ["BG-1", "BG-DG"]:
                smooth = 5
            stat.channel_busy_time, stat.channel_busy_n = smooth_timeline(stat.channel_busy_time, stat.channel_busy_n, smooth)
            for x, y in zip(stat.channel_busy_time, stat.channel_busy_n):
                writer.writerow([config, x, y])

def dump_overall_latency_breakdown(stat_dict):
    df = overall_latency_pd(stat_dict)
    df.to_csv('overall_latency_breakdown.csv', index=False)

def dump_sample_latency_breakdown(stat_dict):
    df = sample_latency_pd(stat_dict)
    df.to_csv('command_latency_breakdown.csv', index=False)

def dump_speedup(stat_dict):
    dic = speedup_dict(stat_dict)
    with open('speedup.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['config', 'latency', 'speedup'])
        for config, latency, speedup in zip(dic['config'], dic['latency'], dic['speedup']):
            writer.writerow([config, latency, speedup])

def dump_hop_breakdown(stat_dict):
    latency_dict = {}
    col_names = ['config']
    for label, stat in stat_dict.items():
        latency_dict[label] = []
        for hop in range(stat.num_hop+1):
            latency_dict[label].append(stat.hop_start_time[hop])
            latency_dict[label].append(stat.hop_end_time[hop])
        
        if len(col_names) == 1:
            for hop in range(stat.num_hop+1):
                col_names += [f'hop_{hop}_start', f'hop_{hop}_end' ]
    with open('hop_latency_breakdown.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(col_names)
        for label, latency_list in latency_dict.items():
            writer.writerow([label] + latency_list)

def dump_energy(stat_dict):
    energy_dict = {}
    energy_dict['CC'] = cpu_centric_energy(stat_dict['BG-1'])
    
    for config, stat in stat_dict.items():
        energy = isc_energy(stat)
        energy_dict[config] = energy
    
    keys = set()
    for config, energy in energy_dict.items():
        keys.update(energy.keys())
    
    with open('energy.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['config'] + list(keys))
        for config, energy in energy_dict.items():
            row = [config]
            for key in keys:
                val = energy.get(key, 0)
                row.append(val)
            writer.writerow(row)