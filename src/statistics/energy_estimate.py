from ssd_config import ssd_config
from system_config import system_config, set_system_config
from util import *

ssd_voltage_v = 3.3
die_current_read_ma = 25
channel_current_busidle_ma = 5
channel_current_stdby_ua = 10

host_ddr3_energy_pj_bit = 70 # 50-75
host_ddr4_energy_pj_bit = 40 # 22-40
ssd_dram_energy_pj_bit = 22 # 22-40

pcie3_port_energy_pj_bit = 8.9 # 7 for lowest
pcie4_port_energy_pj_bit = 7.5
pcie5_port_energy_pj_bit = 11.4


def channel_energy_mj(channel_total_n, channel_busy_time_us, channel_busy_n):
    total_energy_uj = 0
    active_power_mw = channel_current_busidle_ma * ssd_voltage_v
    idle_power_mw = channel_current_stdby_ua * ssd_voltage_v / 1e3
    for i in range(len(channel_busy_time_us) - 1):
        delta_time_us = channel_busy_time_us[i + 1] - channel_busy_time_us[i]
        
        channel_idle_n = channel_total_n - channel_busy_n[i]
        total_energy_uj += delta_time_us * (channel_busy_n[i] * active_power_mw + channel_idle_n * idle_power_mw) / 1e3
    total_energy_mj = total_energy_uj / 1e3
    return total_energy_mj

def chip_energy_mj(chip_busy_time_us, chip_busy_n):
    total_energy_uj = 0
    active_power_mw = die_current_read_ma * ssd_voltage_v
    for i in range(len(chip_busy_time_us) - 1):
        delta_time_us = chip_busy_time_us[i + 1] - chip_busy_time_us[i]
        total_energy_uj += delta_time_us * chip_busy_n[i] * active_power_mw / 1e3
    total_energy_mj = total_energy_uj / 1e3
    return total_energy_mj

def ssd_pcie_energy_mj(transfer_byte, pcie_gen):
    transfer_bit = transfer_byte * 8
    # 4 * port_energy:
    # cpu 1, pcie switch 2, ssd 1 
    if pcie_gen == 3:
        energy_pj_bit = 4 * pcie3_port_energy_pj_bit
    elif pcie_gen == 4:
        energy_pj_bit = 4 * pcie4_port_energy_pj_bit
    elif pcie_gen == 5:
        energy_pj_bit = 4 * pcie5_port_energy_pj_bit
    else:
        print("pcie_gen not supported")
        exit(1)
    total_energy_mj = transfer_bit * energy_pj_bit / 1e9

    return total_energy_mj

def accel_pcie_energy_mj(transfer_byte, pcie_gen):
    transfer_bit = transfer_byte * 8
    # 2 * port_energy:
    # cpu 1, accelerator 1 
    if pcie_gen == 3:
        energy_pj_bit = 2 * pcie3_port_energy_pj_bit
    elif pcie_gen == 4:
        energy_pj_bit = 2 * pcie4_port_energy_pj_bit
    elif pcie_gen == 5:
        energy_pj_bit = 2 * pcie5_port_energy_pj_bit
    else:
        print("pcie_gen not supported")
        exit(1)
    total_energy_mj = transfer_bit * energy_pj_bit / 1e9

    return total_energy_mj

def host_ddr_energy_mj(transfer_byte, ddr_gen):
    transfer_bit = transfer_byte * 8
    if ddr_gen == 3:
        energy_pj_bit = host_ddr3_energy_pj_bit
    elif ddr_gen == 4:
        energy_pj_bit = host_ddr4_energy_pj_bit
    else:
        print("ddr_gen not supported")
        exit(1)
    total_energy_mj = transfer_bit * energy_pj_bit / 1e9

    return total_energy_mj

def ssd_dram_energy_mj(transfer_byte):
    transfer_bit = transfer_byte * 8
    energy_pj_bit = ssd_dram_energy_pj_bit
    total_energy_mj = transfer_bit * energy_pj_bit / 1e9

    return total_energy_mj

def accel_compute_energy_mj(num_ops, tech_node_nm):
    total_energy_mj = 0
    energy_table_pj = {'add8':0.03, 'add32':0.1, 'mul8':0.2, 'mul32':3.1, 'fadd16': 0.4, 'fadd32':0.9, 'fmul16':1.1, 'fmul32':3.7}
    for op, num in num_ops.items():
        total_energy_mj += num * energy_table_pj[op]
    total_energy_mj /= 1e9
    total_energy_mj *= (tech_node_nm/45)**2
    return total_energy_mj

def accel_sram_energy_mj(num_read_byte, num_write_byte, busy_time_us, idle_time_us):
    dynamic_read_nj_bit = 0.46176 / 512
    dynamic_write_nj_bit = 0.482218 / 512
    standby_leakage_mw = 2559.02
    gate_leakage_mw = 131.189
    
    read_energy_mj = (num_read_byte * 8) * dynamic_read_nj_bit / 1e6
    write_energy_mj = (num_write_byte * 8) * dynamic_write_nj_bit / 1e6
    static_energy_mj = (standby_leakage_mw * busy_time_us + gate_leakage_mw * idle_time_us) / 1e6
    
    total_energy_mj = read_energy_mj + write_energy_mj + static_energy_mj
    return total_energy_mj

def accel_energy_mj(stat):
    energy_dict = {}
    
    busy_time_us = stat.dnn_end_time[-1] - stat.dnn_start_time[-1]
    idle_time_us = stat.dnn_start_time[-1] - busy_time_us
    energy_dict['dnn sram'] = accel_sram_energy_mj(stat.sram_read_byte, stat.sram_write_byte, busy_time_us, idle_time_us)
    
    num_ops = {'fadd16': stat.accel_n_mac, 'fmul16': stat.accel_n_mac}
    energy_dict['dnn compute'] = accel_compute_energy_mj(num_ops, 32)
    
    return energy_dict

def cpu_centric_energy(stat):
    energy_dict = {}
    energy_dict["flash channel"] = channel_energy_mj(ssd_config.num_channel, stat.channel_busy_time, stat.channel_busy_n)
    energy_dict["flash chip"] = chip_energy_mj(stat.chip_busy_time, stat.chip_busy_n)
    
    total_pg_sz = sum(stat.n_page_per_hop) * 4096
    total_vec_sz =  batch_size() * total_sample() * graph_params['feat_sz']

    ssd_pcie_energy = ssd_pcie_energy_mj(total_pg_sz, pcie_gen=4)
    accel_pcie_energy = accel_pcie_energy_mj(total_vec_sz, pcie_gen=4)
    energy_dict["pcie"] = ssd_pcie_energy + accel_pcie_energy
    
    main_memory_energy = host_ddr_energy_mj(total_pg_sz + total_vec_sz, ddr_gen=4)
    energy_dict["main memory"] = main_memory_energy

    ssd_dram_energy = 2 * ssd_dram_energy_mj(total_pg_sz)
    energy_dict['ssd dram'] = ssd_dram_energy
    
    energy_dict.update(accel_energy_mj(stat))
    return energy_dict

def isc_energy(stat):
    energy_dict = {}
    energy_dict["flash channel"] = channel_energy_mj(ssd_config.num_channel, stat.channel_busy_time, stat.channel_busy_n)
    energy_dict["flash chip"] = chip_energy_mj(stat.chip_busy_time, stat.chip_busy_n)
    
    energy_dict["ssd dram"] = 2 * ssd_dram_energy_mj(stat.dram_read_byte)

    energy_dict.update(accel_energy_mj(stat))

    return energy_dict

# https://github.com/Accelergy-Project/accelergy-aladdin-plug-in/tree/master
# https://github.com/Accelergy-Project/accelergy-cacti-plug-in