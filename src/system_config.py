import configparser
import os

class SystemConfig():
    def __init__(self):
        self.valid_config = False
    
    def read_conf_file(self, conf_file):
        config = configparser.ConfigParser()
        config.read(conf_file)

        self.name = config.get('general', 'name')

        self.host_side_delay_us = float(config.get('host', 'host_side_delay_us'))
        self.pcie_bw_mbps = float(config.get('host', 'pcie_bw_mbps'))

        self.flash_sample = config.getboolean('device', 'flash_sample')
        self.channel_forward = config.getboolean('device', 'channel_forward')
        self.sync_hop = config.getboolean('device', 'sync_hop')
        self.sync_host = config.getboolean('device', 'sync_host')
        self.dram_translate = config.getboolean('device', 'dram_translate')

        self.valid_config = True

    def dump(self):
        if not self.valid_config:
            print('Error: invalid system config')
            return
        print('------------------------------------')
        print('name:               ', self.name)
        print('host_side_delay_us: ', self.host_side_delay_us)
        print('pcie_bw_mbps:       ', self.pcie_bw_mbps)
        print('flash_sample:       ', self.flash_sample)
        print('channel_forward:    ', self.channel_forward)
        print('sync_hop:           ', self.sync_hop)
        print('sync_host:          ', self.sync_host)
        print('dram_translate:     ', self.dram_translate)

system_config = SystemConfig()

def set_system_config(name):
    system_config_path = f'configs/system/{name}.cfg'
    system_config.read_conf_file(system_config_path)

if __name__ == '__main__':
    system_config_path = 'configs/system/'
    for cfg_file in os.listdir(system_config_path):
        if cfg_file.endswith('.cfg'):
            cfg = SystemConfig()
            cfg.read_conf_file(system_config_path + cfg_file)
            cfg.dump()