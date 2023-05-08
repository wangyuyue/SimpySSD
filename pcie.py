import logging
from sim import *
from util import system_params, page_align_sz

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('pcie logger')
logger.setLevel(logging.INFO)

class PCIeQueue:
    def __init__(self):
        self.busy = False
        self.queue = []
    def dequeue(self):
        return self.queue.pop(0)
    def enqueue(self, data_sz):
        self.queue.append(data_sz)
    def empty(self):
        return len(self.queue) == 0

class PCIeBus(Sim):
    def __init__(self, system, node1, node2='host'):
        self.pcie_queue = [PCIeQueue(), PCIeQueue()]
        self.bandwidth = system_params['pcie_bw']
        self.system = system
        self.nodes = [node1, node2]

    def __repr__(self):
        return f"PCIe Bus ({self.nodes[0]}-{self.nodes[1]})"

    def get_queue_dst(self, src):
        for i, node in enumerate(self.nodes):
            if node == src:
                queue = self.pcie_queue[i]
                dst = self.nodes[1-i]
                return queue, dst
        raise Exception("Invalid source node")

    def begin_pcie_transfer(self, data_sz, src):
        queue, dst = self.get_queue_dst(src)
        if queue.busy:
            queue.enqueue(data_sz)
        else:
            queue.busy = True
            aligned_sz = page_align_sz(data_sz)
            end_time = engine.now + aligned_sz / self.bandwidth
            logger.info(f"[{engine.now}]: {self} begin transfer {data_sz}B {src}->{dst}")
            engine.add(Event(self, 'end_pcie_transfer', end_time, {'data_sz': data_sz, 'src': src}))

    def end_pcie_transfer(self, data_sz, src):
        queue, dst = self.get_queue_dst(src)
        queue.busy = False
        logger.info(f"[{engine.now}]: {self} end transfer {data_sz}B {src}->{dst}")
        if 'ssd' in self.nodes:
            end_time = engine.now + system_params['host_side_delay']
            engine.add(Event(self.system, 'notify_app', end_time, {}))

        if not queue.empty():
            data_sz = queue.dequeue()
            self.begin_pcie_transfer(data_sz, src)
    
    def do(self, event):
        if event.func == 'end_pcie_transfer':
            self.end_pcie_transfer(event.args['data_sz'], event.args['src'])
        else:
            super().do(event)