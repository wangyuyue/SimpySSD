from sim import *
from ssd_estimate import SSD
from pcie import PCIeBus
from nn_accel import GNNAcc
from dram_buffer import Buffer
from util import *

class System(Sim):
    def __init__(self):
        self.ssd = SSD(self)
        self.pcie_bus = PCIeBus(self)
        self.gnn_accelerator = GNNAcc(self)

    def set_app(self, app):
        self.app = app
        self.dram_buf = Buffer(graph_params['feat'], 100)

    def process(self, cmd):
        self.app.process(cmd)

    def transfer(self, data_sz):
        self.pcie_bus.begin_pcie_transfer(data_sz)

    def issue_cmd(self, cmd):
        self.ssd.issue(cmd)

    def compute(self):
        self.gnn_accelerator.begin_compute()
    
    def notify_app(self):
        self.app.fetch_page()