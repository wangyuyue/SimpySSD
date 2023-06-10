import configparser
from gnn_topology import GNNTopology
from util import graph_params, app_params
from scalesim.scale_sim import scalesim

class AccelConfig():
    def __init__(self):
        self.valid_config = False
        self.accel_loc = None

    def set_accel_config(self, conf_file):
        self.conf_file = conf_file
        config = configparser.ConfigParser()
        config.read(conf_file)

        self.name = config.get('general', 'run_name')
        self.location = config.get('system', 'location')
        self.freq_mhz = float(config.get('system', 'freq_mhz'))
        self.valid_config = True

    def sim_exec_time(self):
        gnn = GNNTopology(app_params['batch'], app_params['sample_per_hop'], graph_params['feat_sz'] // 2, app_params['output_dim'], app_params['hidden_dim'])
        gnn.gen_topo()
        gnn.dump_csv('gnn_topo.csv')
        
        s = scalesim(save_disk_space=True, verbose=True,
                    config=self.conf_file,
                    topology='gnn_topo.csv',
                    input_type_gemm=True
                    )
        s.run_scale(top_path='./generated')
        total_cyles = s.get_total_cycles()
        return total_cyles / self.freq_mhz

accel_config = AccelConfig()


if __name__ == '__main__':
    accel_config = AccelConfig()
    config_dir = 'configs/accelerator/'
    accel_config.set_accel_config(config_dir+'isc_tpu.cfg')
    # accel_config.set_accel_config(config_dir+'pcie_tpu.cfg')
    exec_time = accel_config.sim_exec_time()
    print(f"Execution time: {exec_time} us")