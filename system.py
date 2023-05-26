from sim import *
from ssd_estimate import SSD
from pcie import PCIeBus
from nn_accel import GNNAcc
from dram import DRAM
from util import *
from sys_stat import *

class System(Sim):
    def __init__(self):
        self.ssd = SSD(self)
        self.ssd_pcie = PCIeBus(self, 'ssd')
        self.gnn_accelerator = GNNAcc(self)
        self.ssd_dram = DRAM(self)
        if system_params['accel_loc'] == 'pcie':
            self.dnn_pcie = PCIeBus(self, 'accel')
        self.app = None
        self.stat = None

    def set_app(self, app):
        self.app = app
        self.ssd_dram.add_buffer(graph_params['feat_sz'], 100)

    def set_stat(self, stat):
        self.stat = stat

    def process(self, cmd):
        self.app.process(cmd)

    def transfer(self, data_sz, src, dst):
        if src == 'ssd' and dst == 'dnn_accel':
            raise Exception("doesn't support direct link")
        if src == 'ssd' and dst == 'host':
            self.ssd_pcie.begin_pcie_transfer(data_sz, src)
        if src == 'host' and dst == 'dnn_accel':
            self.dnn_pcie.begin_pcie_transfer(data_sz, src)  

    def issue_cmd(self, cmd):
        self.stat.cmd_stat[cmd] = CmdStat()
        self.stat.cmd_stat[cmd].set_time('issue', engine.now)
        self.ssd.issue(cmd)

    def check_compute(self):
        if len(self.app.wait_completion) == 0:
            self.compute()

    def compute(self):
        self.gnn_accelerator.begin_compute()
    
    def notify_app(self):
        self.app.fetch_page_sync()
    
    def do(self, event):
        if event.func == 'notify_app':
            self.notify_app()
        elif event.func == 'issue_cmd':
            cmd = event.args['cmd']
            self.issue_cmd(cmd)
        else:
            super().do(event)

