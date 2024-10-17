import configparser

class SSDConfig:
    def __init__(self):
        self.valid_config = False

    def read_conf_file(self, conf_file):
        config = configparser.ConfigParser()
        config.read(conf_file)

        self.channel_bw_mbps = float(config.get('flash', 'channel_bw_mbps'))
        self.read_latency_us = float(config.get('flash', 'read_latency_us'))
        self.write_latency_us = float(config.get('flash', 'write_latency_us'))
        
        self.pg_sz_kb = float(config.get('flash', 'pg_sz_kb'))
        self.num_chip = int(config.get('flash', 'num_chip'))
        self.num_channel = int(config.get('flash', 'num_channel'))

        self.dram_bw_mbps = float(config.get('dram', 'dram_bw_mbps'))
        self.dram_latency_us = float(config.get('dram', 'dram_latency_us'))
        self.dram_capacity_mb = float(config.get('dram', 'dram_capacity_mb'))

        self.n_cores = int(config.get('core', 'n_cores'))

        self.valid_config = True

    def dump(self):
        if not self.valid_config:
            print("Error: invalid ssd config")
            return
        print("channel_bw_mbps:    ", self.channel_bw_mbps)
        print("read_latency_us:    ", self.read_latency_us)
        print("write_latency_us:   ", self.write_latency_us)
        print("pg_sz_kb:           ", self.pg_sz_kb)

        print("num_chip:           ", self.num_chip)
        print("num_channel:        ", self.num_channel)
        
        print("dram_bw_mbps:       ", self.dram_bw_mbps)
        print("dram_latency_us:    ", self.dram_latency_us)
        print("dram_capacity_mb:   ", self.dram_capacity_mb)

        print("n_cores:            ", self.n_cores)

ssd_config = SSDConfig()

if __name__ == '__main__':
    import os
    cfg = ssd_config
    cfg.read_conf_file(os.environ['BG_BASE_DIR'] + '/configs/ssd/traditional_ssd.cfg')
    cfg.dump()