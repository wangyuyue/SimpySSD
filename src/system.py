from sim import *
from ssd_estimate import SSD
from pcie import PCIeBus
from nn_accel import GNNAcc
from dram import DRAM
from util import *
from sys_stat import *
from accel_config import accel_config

class System(Sim):
    def __init__(self):
        self.ssd = SSD(self)
        self.ssd_pcie = PCIeBus(self, 'ssd')
        self.gnn_accelerator = GNNAcc(self)
        self.ssd_dram = DRAM(self)
        if accel_config.accel_loc == 'pcie':
            self.dnn_pcie = PCIeBus(self, 'dnn_accel')
        self.app = None
        self.stat = None

    def set_app(self, app):
        self.app = app
        self.ssd_dram.add_buffer(graph_params['feat_sz'], 100)

    def set_stat(self, stat):
        self.stat = stat

    def process(self, cmd):
        self.app.process(cmd)

    def transfer(self, data_sz, src, dst, data_type):
        if src == 'ssd' and dst == 'host':
            self.ssd_pcie.begin_pcie_transfer(data_sz, src, data_type)
        elif src == 'host' and dst == 'dnn_accel':
            self.dnn_pcie.begin_pcie_transfer(data_sz, src, data_type)
        elif src == 'host' and dst == 'ssd':
            self.ssd_pcie.begin_pcie_transfer(data_sz, src, data_type)
        else:
            print(src, dst)
            raise Exception("Invalid transfer")

    def issue_cmd(self, cmd):
        if self.stat is not None:
            self.stat.cmd_stat[cmd] = CmdStat()
            self.stat.cmd_stat[cmd].set_time('issue', engine.now)
        self.ssd.issue(cmd)

    def check_compute(self):
        if len(self.app.wait_completion) == 0:
            self.compute()

    def compute(self):
        self.gnn_accelerator.begin_compute()
    
    def notify_app(self, pcie_args):
        self.app.get_pcie_notified(pcie_args)
    
    def do(self, event):
        if event.func == 'notify_app':
            self.notify_app(event.args)
        elif event.func == 'issue_cmd':
            cmd = event.args['cmd']
            self.issue_cmd(cmd)
        else:
            super().do(event)


