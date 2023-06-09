import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from sys_stat import Stat
from util import *
from ssd_config import ssd_config

sns.set_theme()
# marker: s(square), o(circle)
# linestyle -(solid), --(dash)

def total(time, value):
    total = 0
    for i, t in enumerate(time):
        if i < len(time) - 1:
            total += value[i] * (time[i+1] - time[i])
    return total

def smooth_timeline(time, value, unit):
    cur = time[0] - time[0] % unit
    ti = 0
    smooth_time = [cur]
    smooth_value = [0]
    
    while cur < time[-1]:
        if time[ti] < smooth_time[-1] + unit:
            if ti > 0:
                smooth_value[-1] += value[ti-1] * (time[ti] - cur)
            cur = time[ti]
            ti += 1
        else:
            if ti > 0:
                smooth_value[-1] += value[ti-1] * (smooth_time[-1] + unit - cur)
            cur = smooth_time[-1] + unit
            smooth_time.append(cur)
            smooth_value.append(0)

    smooth_value = [value/unit for value in smooth_value]

    return smooth_time, smooth_value

def average_timeline(timeseries):
    times = []
    for time, _ in timeseries:
        times.extend(time)
    times = sorted(set(times))
    new_values = []
    for time, value in timeseries:
        new_value = [0]
        i = 0
        for t in times:
            if t < time[i]:
                new_value.append(new_value[-1])
            else:
                new_value.append(value[i])
                if i < len(time) - 1:
                    i += 1
        new_value.pop(0)
        new_values.append(new_value)
    avg_value = [sum(tup)/len(tup) for tup in zip(*new_values)]
    return times, avg_value

def plot_chip_utilization(stat_dict):
    def draw(sample, smooth=None):
        plt.figure()
        for label, stat in stat_dict.items():
            if ('sample' in label) ^ sample:
                continue
            x = stat.chip_busy_time
            y = stat.chip_busy_n
            if smooth != None:
                x, y = smooth_timeline(x, y, smooth)
            plot = sns.lineplot(x=x, y=y, drawstyle='steps-post', label=label, linestyle='-')
            plot.set(xlabel='time (us)', ylabel='chip utilization')
        if sample:
            plt.savefig("chip_utilization_sample.png")
        else:
            plt.savefig("chip_utilization.png")
    draw(sample=True)
    draw(sample=False, smooth=5)

def plot_channel_utilization(stat_dict):
    def draw(sample, smooth=None):
        plt.figure()
        for label, stat in stat_dict.items():
            if ('sample' in label) ^ sample:
                continue
            x = stat.channel_busy_time
            y = stat.channel_busy_n
            if smooth != None:
                x, y = smooth_timeline(x, y, smooth)
            plot = sns.lineplot(x=x, y=y, drawstyle='steps-post', label=label, linestyle='-')
            plot.set(xlabel='time (us)', ylabel='channel utilization')
        if sample:
            plt.savefig("channel_utilization_sample.png")
        else:
            plt.savefig("channel_utilization.png")
    draw(sample=True, smooth=20)
    draw(sample=False, smooth=1)


def plot_overall_latency_breakdown(stat_dict):
    plt.figure()
    plt.tight_layout()
    breakdown_list = []
    for label, stat in stat_dict.items():
        if not 'sample' in label:
            continue
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
    df.plot(x='config', kind='bar', stacked=True, rot=15, title='Latency breakdown', xlabel='config', ylabel='latency (us)')
    plt.savefig("overall_latency_breakdown.png", bbox_inches="tight")

def plot_sample_latency_breakdown(stat_dict):
    plt.figure()
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
        breakdown_list.append(breakdown)

    df = pd.DataFrame(breakdown_list, index=configs)
    df.plot.barh(stacked=True, xlabel='latency (us)', ylabel='config', title='Command latency breakdown')
    plt.savefig("command_latency_breakdown.png", bbox_inches="tight")

def plot_speedup(stat_dict):
    plt.figure()
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.rcParams["xtick.labelsize"] = 10
    dic = {'config': [], 'latency': []}
    for label, stat in stat_dict.items():
        dic['config'].append(label)
        dic['latency'].append(stat.total_time)
    baseline = max(dic['latency'])
    dic['speedup'] = [baseline/lat for lat in dic['latency']]
    plot = sns.barplot(x='config', y='speedup', data=dic)
    plot.set(xlabel='config', ylabel='speedup')
    plt.savefig("speedup.png", bbox_inches="tight")


def plot_hop_breakdown(stat_dict):
    plt.figure()
    breakdown_list = []
    configs = []
    for label, stat in stat_dict.items():
        configs.append(label)
        hop_latency = []
        for hop in range(stat.num_hop+1):
            if hop < stat.num_hop:
                hop_latency.append(stat.hop_start_time[hop+1] - stat.hop_start_time[hop])
            else:
                hop_latency.append(stat.hop_end_time[hop] - stat.hop_start_time[hop])
        breakdown = {f'hop_{i}': lat for i, lat in enumerate(hop_latency)}
        breakdown_list.append(breakdown)
    df = pd.DataFrame(breakdown_list, index=configs)
    df.plot.barh(stacked=True, xlabel='latency (us)', ylabel='config', title='Hop latency breakdown')
    plt.savefig("hop_latency_breakdown.png", bbox_inches="tight")
