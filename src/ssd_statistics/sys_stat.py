class CmdStat:
    def __init__(self):
        self.time = {}
    def set_time(self, typ, time):
        assert(typ in ['issue', 'read_begin', 'transfer_begin', 'transfer_end'])
        self.time[typ] = time

class Stat:
    def __init__(self, num_hops):
        self.num_hop = num_hops

        self.hop_start_time = [-1] * (self.num_hop + 1)
        self.hop_end_time = [0] * (self.num_hop + 1)
        
        self.channel_busy_n = []
        self.channel_busy_time = []
        
        self.chip_busy_n = []
        self.chip_busy_time = []
        
        self.dnn_start_time = []
        self.dnn_end_time = []
        
        self.pcie_start_time = {}
        self.pcie_end_time = {}
        
        self.ftl_start_time = []
        self.ftl_end_time = []

        self.total_host_delay = 0

        self.total_time = 0

        self.cmd_stat = {}

        self.n_page_per_hop = [0] * (self.num_hop + 1)

        self.sram_read_byte = 0
        self.sram_write_byte = 0
        self.accel_n_mac = 0

        self.dram_read_byte = 0
        self.dram_write_byte = 0

    def channel_busy(self, now_time, delta):
        if len(self.channel_busy_n) == 0:
            self.channel_busy_time.append(now_time)
            self.channel_busy_n.append(delta)
            # print(self.channel_busy_n)
            return

        now_busy_n = self.channel_busy_n[-1] + delta
        if self.channel_busy_time[-1] == now_time:
            self.channel_busy_n[-1] = now_busy_n
        else:
            assert(self.channel_busy_time[-1] < now_time)
            self.channel_busy_time.append(now_time)
            self.channel_busy_n.append(now_busy_n)
        # print(self.channel_busy_n)
    
    def chip_busy(self, now_time, delta):
        if len(self.chip_busy_n) == 0:
            self.chip_busy_time.append(now_time)
            self.chip_busy_n.append(delta)
            # print(self.chip_busy_n)
            return

        now_busy_n = self.chip_busy_n[-1] + delta
        if self.chip_busy_time[-1] == now_time:
            self.chip_busy_n[-1] = now_busy_n
        else:
            assert(self.chip_busy_time[-1] < now_time)
            self.chip_busy_time.append(now_time)
            self.chip_busy_n.append(now_busy_n)
        # print(self.chip_busy_n)

    def start_hop(self, now_time, n_hop):
        if self.hop_start_time[n_hop] < 0:
            self.hop_start_time[n_hop] = now_time
        else:
            assert(self.hop_start_time[n_hop] <= now_time)
        # print("start time", self.hop_start_time)

    def end_hop(self, now_time, n_hop):
        assert(self.hop_end_time[n_hop] <= now_time)
        self.hop_end_time[n_hop] = now_time
        # print("end time", self.hop_end_time)

    def start_dnn(self, now_time):
        self.dnn_start_time.append(now_time)

    def end_dnn(self, now_time):
        self.dnn_end_time.append(now_time)

    def start_pcie(self, now_time, from_node, to_node):
        pair = f'{from_node}->{to_node}'
        if not pair in self.pcie_start_time:
            self.pcie_start_time[pair] = [now_time]
        else:
            self.pcie_start_time[pair].append(now_time)
        print(pair, self.pcie_start_time[pair])
    
    def end_pcie(self, now_time, from_node, to_node):
        pair = f'{from_node}->{to_node}'
        if not pair in self.pcie_end_time:
            self.pcie_end_time[pair] = [now_time]
        else:
            self.pcie_end_time[pair].append(now_time)
        print(pair, self.pcie_end_time[pair])

    def start_ftl(self, now_time):
        self.ftl_start_time.append(now_time)

    def end_ftl(self, now_time):
        self.ftl_end_time.append(now_time)

    def host_delay(self, delay):
        self.total_host_delay += delay

    def set_accel_stat(self, accel_config):
        self.sram_read_byte = accel_config.sram_read_byte
        self.sram_write_byte = accel_config.sram_write_byte
        self.accel_n_mac = accel_config.n_mac