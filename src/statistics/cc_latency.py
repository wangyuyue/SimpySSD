from .sys_stat import Stat

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
    total_latency += sum(ssd_pcie)

    return total_latency