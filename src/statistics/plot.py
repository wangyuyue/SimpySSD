import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from .series_process import smooth_timeline
from .dataframe import *

sns.set_theme()
# marker: s(square), o(circle)
# linestyle -(solid), --(dash)

def plot_chip_utilization(stat_dict):
    def draw(sample, smooth=None):
        plt.figure()
        for label, stat in stat_dict.items():
            if (label in ["BG-1", "BG-DG"]) ^ (not sample):
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
            if (label in ["BG-1", "BG-DG"]) ^ (not sample):
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
    df = overall_latency_pd(stat_dict)
    df.plot(x='config', kind='bar', stacked=True, rot=15, title='Latency breakdown', xlabel='config', ylabel='latency (us)')
    plt.savefig("overall_latency_breakdown.png", bbox_inches="tight")

def plot_sample_latency_breakdown(stat_dict):
    plt.figure()
    df = sample_latency_pd(stat_dict)
    df.plot.barh(stacked=True, xlabel='latency (us)', ylabel='config', title='Command latency breakdown')
    plt.savefig("command_latency_breakdown.png", bbox_inches="tight")

def plot_speedup(stat_dict):
    plt.figure()
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.rcParams["xtick.labelsize"] = 10
    dic = speedup_dict(stat_dict)
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