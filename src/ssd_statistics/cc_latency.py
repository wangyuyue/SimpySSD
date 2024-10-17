from .sys_stat import Stat
from util import *

# estimate of cpu-centric system latency breakdown
def cc_latency_breakdown(stat):
    pcie_gen = 4
    last_transfer_kb = stat.last_transfer_kb
    pg_sz_kb = 4

    breakdown = {}
    breakdown['host'] = stat.total_host_delay

    hop_duration = [stat.hop_end_time[i] - stat.hop_start_time[i] for i in range(stat.num_hop + 1)]
    breakdown['flash'] = sum(hop_duration)

    ssd_pcie = sum([n_page * pg_sz_kb / 2**(pcie_gen - 1) for n_page in stat.n_page_per_hop])
    last_hop_accel_pcie = last_transfer_kb  / 2**(pcie_gen - 1)
    breakdown['pcie'] = ssd_pcie + last_hop_accel_pcie

    assert(len(stat.dnn_start_time) == 1)
    accel_time = stat.dnn_end_time[-1] - stat.dnn_start_time[-1]
    breakdown['dnn'] = accel_time

    return breakdown


def cc_total_latency(stat):
    pcie_gen = 4
    pg_sz_kb = 4
    
    total_latency = 0
    
    total_latency += stat.total_host_delay

    hop_duration = [stat.hop_end_time[i] - stat.hop_start_time[i] for i in range(stat.num_hop + 1)]
    total_latency += sum(hop_duration)

    ssd_pcie = [n_page * pg_sz_kb / 2**(pcie_gen - 1) for n_page in stat.n_page_per_hop]
    
    smartsage_transfer = 0
    n_total_sample = app_params['batch']
    for n_sample in app_params['sample_per_hop']:
        smartsage_transfer += page_align_sz(n_total_sample * (n_sample * 4 + graph_params['feat_sz']))
        n_total_sample *= n_sample
    smartsage_transfer += page_align_sz(n_total_sample * graph_params['feat_sz'])
    smartsage_pcie = smartsage_transfer / 1e3 / 2**(pcie_gen - 1)

    glist_pcie = sum(ssd_pcie[:-1])
    glist_pcie += page_align_sz(app_params['batch'] * 27 * graph_params['feat_sz']) / 1e3 / 2**(pcie_gen - 1)

    cc_latency = total_latency + sum(ssd_pcie)
    smartsage_latency = total_latency + smartsage_pcie
    glist_latency = total_latency + glist_pcie
    
    print(f"CC: {cc_latency} (us)")
    print(f"SmartSage: {smartsage_latency} (us), speedup {cc_latency/smartsage_latency}")
    print(f"GList: {glist_latency} (us), speedup {cc_latency/glist_latency}")

    total_latency += sum(ssd_pcie)

    return total_latency