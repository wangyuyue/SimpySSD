import logging
from sim import *
from system_config import system_config
from accel_config import accel_config

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('acc logger')
logger.setLevel(logging.INFO)

class GNNAcc(Sim):
    idle = 0
    computing = 1
    def __init__(self, system):
        self.location = accel_config.accel_loc
        self.compute_latency = accel_config.latency_us
        self.status = GNNAcc.idle
        
        self.system = system

    def __repr__(self):
        return f'GNNAcc'

    def begin_compute(self):
        self.status = GNNAcc.computing
        logger.info(f"[{engine.now}]: {self} begin compute")
        engine.add(Event(self, 'end_compute', engine.now + self.compute_latency, {}))

        if self.system.stat is not None:
            self.system.stat.start_dnn(engine.now)
        
    def end_compute(self):
        self.status = GNNAcc.idle
        logger.info(f"[{engine.now}]: {self} end compute")

        if self.system.stat is not None:
            self.system.stat.end_dnn(engine.now)

    def do(self, event):
        if event.func == 'end_compute':
            self.end_compute()
        else:
            super().do(event)