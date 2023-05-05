import logging
from sim import *
from util import ssd_params, page_align_sz

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('pcie logger')
logger.setLevel(logging.INFO)

class PCIeBus(Sim):
    def __init__(self, system):
        self.pcie_queue = []
        self.pcie_busy = False
        self.bandwidth = ssd_params['pcie_bw']
        self.system = system

    def __repr__(self):
        return "PCIe Bus"

    def begin_pcie_transfer(self, data_sz):
        if self.pcie_busy:
            self.pcie_queue.append(data_sz)
        else:
            self.pcie_busy = True
            aligned_sz = page_align_sz(data_sz)
            end_time = engine.now + aligned_sz / self.bandwidth
            logger.info(f"[{engine.now}]: {self} begin transfer data ({data_sz}B)")
            engine.add(Event(self, 'end_pcie_transfer', end_time, {'data_sz': data_sz}))

    def end_pcie_transfer(self, data_sz):
        self.pcie_busy = False
        logger.info(f"[{engine.now}]: {self} end transfer data ({data_sz}B)")
        self.system.notify_app()

        if len(self.pcie_queue) > 0:
            data_sz = self.pcie_queue.pop(0)
            self.begin_pcie_transfer(data_sz)
    
    def do(self, event):
        if event.func == 'end_pcie_transfer':
            self.end_pcie_transfer(event.args['data_sz'])
        else:
            super().do(event)