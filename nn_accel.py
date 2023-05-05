import logging
from sim import *
from util import ssd_params

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('acc logger')
logger.setLevel(logging.INFO)

class GNNAcc(Sim):
    idle = 0
    computing = 1
    def __init__(self, system):
        self.location = 'separate'
        self.compute_latency = 50
        self.status = GNNAcc.idle
        
        self.system = system

    def __repr__(self):
        return f'GNNAcc'

    def begin_compute(self):
        self.status = GNNAcc.computing
        logger.info(f"[{engine.now}]: {self} begin compute")
        engine.add(Event(self, 'end_compute', engine.now + self.compute_latency, {}))

    def end_compute(self):
        self.status = GNNAcc.idle
        logger.info(f"[{engine.now}]: {self} end compute")
        return

    def do(self, event):
        if event.func == 'end_compute':
            self.end_compute()
        else:
            super().do(event)