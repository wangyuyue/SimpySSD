import configparser
from gnn_topology import GNNTopology
from util import graph_params, app_params
from scale_sim import scalesim
import os
import csv

class AccelConfig():
    def __init__(self):
        self.valid_config = False
        self.accel_loc = None
        self.generated_dir = f"{os.environ['BG_BASE_DIR']}/generated/"

    def set_accel_config(self, conf_file):
        self.conf_file = conf_file
        config = configparser.ConfigParser()
        config.read(conf_file)

        self.name = config.get('general', 'run_name')
        self.n_pe = int(config.get('architecture_presets', 'ArrayHeight')) *\
                    int(config.get('architecture_presets', 'ArrayWidth'))

        self.location = config.get('system', 'location')
        self.freq_mhz = float(config.get('system', 'freq_mhz'))
        self.valid_config = True

        self.got_statistics = False

        self.output_dir=f"{self.generated_dir}/{self.name}"

    def sim_exec_time(self):
        cached_file = f"{self.output_dir}/Cached_result.csv"
        # if Summary file does not exist, generate the csv header
        if not os.path.exists(cached_file):
            os.makedirs(self.output_dir, exist_ok=True)
            with open(cached_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['batch', 'sample_per_hop', 'feat_sz', 'latency_us', 'n_mac', 'sram_read_byte', 'sram_write_byte'])

        batch = app_params['batch']
        sample_per_hop = app_params['sample_per_hop']
        str_sample_per_hop = '_'.join([str(sample) for sample in sample_per_hop])
        feat_sz = graph_params['feat_sz']

        with open(cached_file) as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if int(row[0]) == batch and row[1] == str_sample_per_hop and int(row[2]) == feat_sz:
                    self.latency_us, self.n_mac, self.sram_read_byte, self.sram_write_byte = map(float, row[3:])
                    print("Use cached result")
                    return self.latency_us

        with open(cached_file, 'a') as f:
            writer = csv.writer(f)
            gnn = GNNTopology(batch, sample_per_hop, feat_sz // 2, app_params['output_dim'], app_params['hidden_dim'])
            gnn.gen_topo()
            gnn.dump_csv('gnn_topo.csv')
        
            s = scalesim(save_disk_space=True, verbose=False,
                    config=self.conf_file,
                    topology='gnn_topo.csv',
                    input_type_gemm=True
                    )
            s.run_scale(top_path=self.generated_dir)
            total_cyles = s.get_total_cycles()

            self.latency_us = total_cyles / self.freq_mhz
            self.get_statistics()
            writer.writerow([batch, str_sample_per_hop, feat_sz, self.latency_us, self.n_mac, self.sram_read_byte, self.sram_write_byte])
            return self.latency_us
    
    def get_statistics(self):
        self.n_mac = 0
        self.n_layer = 0
        self.layer_cycle = []
        with open(f"{self.output_dir}/COMPUTE_REPORT.csv") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            # print("compute cycle, compute util")
            for row in reader:
                compute_util = float(row[5])
                compute_cycle = int(row[1])
                self.layer_cycle.append(compute_cycle)
                self.n_layer += 1
                self.n_mac += self.n_pe * compute_cycle * compute_util / 100
                # print(compute_cycle, compute_util)
        
        sram_read = 0
        sram_write = 0
        with open(f"{self.output_dir}/BANDWIDTH_REPORT.csv") as f:
            reader = csv.reader(f)
            next(reader)
            # print("IF_MAP Bandwidth, FILTER Bandwidth, OF_MAP Bandwidth")
            for row, cycle in zip(reader, self.layer_cycle):
                ifmap_bw = float(row[1])
                filter_bw = float(row[2])
                ofmap_bw = float(row[3])
                sram_read += (ifmap_bw + filter_bw + ofmap_bw) * cycle
                sram_write += ofmap_bw * cycle
                # print(ifmap_bw, filter_bw, ofmap_bw)
        # every access is 16-bit
        self.sram_read_byte = 2 * sram_read
        self.sram_write_byte = 2 * sram_write
        # print(self.n_mac, self.sram_read_byte, self.sram_write_byte)

accel_config = AccelConfig()


if __name__ == '__main__':
    accel_config = AccelConfig()
    accel_config.set_accel_config(os.environ['BG_BASE_DIR']+'/configs/accelerator/isc_tpu.cfg')
    exec_time = accel_config.sim_exec_time()
    print(f"Execution time: {exec_time} us")